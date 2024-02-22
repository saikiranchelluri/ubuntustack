from rest_framework import status
from rest_framework.response import Response
from users.mongoDb_connection import dashboard_data,users_registration,Reason,critical_enablers,subscriptions_collection,Cost_Details
from rest_framework.views import APIView
from nodemap.edit_actions import edit_actions_gpt_update,add_actions_gpt,generate_description_actions_gpt
from nodemap.milestone import edit_milestones_gpt,Add_Actions_For_milestones_gpt,Add_milestones_validate_title_gpt,Add_milestones_gpt,Add_actions_ce_for_milestone_gpt,Add_Actions_For_milestones_gpt1
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
from bson import ObjectId
import datetime
from datetime import datetime
import uuid
import json
from nodemap.validate_nodemap import convert_date,nodemap_journey,new_nodemap,intermediate_validate,\
    generate_milestone_actions,nodemap_date_to_string,find_mile_type,add_intermediate,append_new_intermediate,\
    date_difference,calculate_timeline,days_between,get_index,new_target_nodemap,\
    north_star_milestone,validate_addintermediate_title,update_milestone_timeline,milestone_progress,north_star_progress,\
    edit_inter_restructure,north_star_progress_milestone,north_star_progress_restructure
from openai.error import ServiceUnavailableError, RateLimitError

'''Get Nodemap Details'''
class Nodemap(APIView):
     def get(self, request, pk):
        try:
            subscription = subscriptions_collection.find_one({'user_id':pk})
            if subscription:
                if subscription['status'] == 'active' or subscription['status'] == 'canceled':
                    nodemap = dashboard_data.find_one({'user_id':pk})
                    if not nodemap:
                        return Response({"message": "No data found"}, status=status.HTTP_400_BAD_REQUEST)
                    nodemap_id = nodemap.pop('_id')
                    dates_to_string = nodemap_date_to_string(nodemap['milestones'])
                    return Response({"nodemap_id": str(nodemap_id),"nodemap" :dates_to_string},status=status.HTTP_200_OK)      
                else:
                    return Response({"message": "Payment not done. Please make the payment."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"message": "Payment not done. Please make the payment."}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
  
"""Edit CE"""
class Edit_CE_View(APIView):
     def patch(self, request,id):
        try:
            request_body = request.body
            request_data = json.loads(request_body)
            milestone_id=request_data[0]["milestone_id"]
            nodemap = dashboard_data.find_one({'_id': ObjectId(id)})
            if not nodemap:
                return Response({"message": "nodemap not found"}, status=status.HTTP_400_BAD_REQUEST)
            mile_obj = dashboard_data.find_one({ "milestones": { '$elemMatch': { "milestone_id": milestone_id } }})
            if not mile_obj:
                return Response({"message": "Invalid Milestone ID"}, status=status.HTTP_400_BAD_REQUEST)    
            nodemap_data=nodemap["milestones"]
            milestone_details = next((item for item in nodemap_data if item["milestone_id"] == milestone_id), None)
            enablers=milestone_details["enablers"]
            for data in request_data:
                ce_id=data["ce_id"]          
                for enabler in enablers:
                    if enabler["enabler_id"]==int(ce_id):
                        if "title" in data:
                            title=data["title"]
                            enabler["title"]=title
                        if "progress" in data:
                            progress=data["progress"]
                            enabler["progress"]=progress
                        enabler["updated_on"] = datetime.now()
            if milestone_details["type"] != "targeted_role":
                mile_progress=milestone_progress(milestone_details["actions"],milestone_details["enablers"])
                milestone_details["progress"]=mile_progress
                milestone_details["updated_on"]=datetime.now()
                if milestone_details["progress"]==100 :
                    northstar_progress=north_star_progress(nodemap["milestones"])
                    mile_data=nodemap["milestones"][-1]
                    mile_progress=milestone_progress(mile_data["actions"],mile_data["enablers"])
                    n_progress=(100/len(nodemap["milestones"]))*(mile_progress/100)
                    if  isinstance(n_progress,float):
                       nstar_progress=round(n_progress, 2)
                    if isinstance(n_progress,int):
                       nstar_progress=n_progress
                    mile_data["progress"]=northstar_progress+nstar_progress
                    mile_data["updated_on"]=datetime.now()
            if milestone_details["type"] == "targeted_role":
                northstar_progress=north_star_progress(nodemap["milestones"])
                mile_progress=milestone_progress(milestone_details["actions"],milestone_details["enablers"])
                n_progress=(100/len(nodemap["milestones"]))*(mile_progress/100)
                if isinstance(n_progress,float):
                   nstar_progress=round(n_progress, 2)
                if isinstance(n_progress,int):
                   nstar_progress=n_progress
                milestone_details["progress"]=northstar_progress+nstar_progress
                milestone_details["updated_on"]=datetime.now()

                        
            dashboard_data.update_one({'_id': ObjectId(id)}, {'$set': nodemap})
            return Response({"message": "updated sucessfully"},status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#Edit Action

#validate Action title

class Edit_Action_Title_Validation_View(APIView):
    def post(self, request):
        try:
            request_body = request.body
            request_data = json.loads(request_body)
            id=request_data["id"]
            action_data=request_data["action_data"]
            milestone_id=action_data[0]["milestone_id"]
            nodemap = dashboard_data.find_one({'_id': ObjectId(id)})
            if not nodemap:
                return Response({"message": "nodemap not found"}, status=status.HTTP_400_BAD_REQUEST)
            #check milestone id is matching or not
            mile_obj = dashboard_data.find_one({ "milestones": { '$elemMatch': { "milestone_id": milestone_id } }})
            if not mile_obj:
                return Response({"message": "Invalid Milestone ID"}, status=status.HTTP_400_BAD_REQUEST)
            user_id=nodemap["user_id"]
            user_data = users_registration.find_one({'_id': ObjectId(user_id)})
            current_role = user_data['questionnaire']['career_runway_role_description']
            nodemap_data=nodemap["milestones"]
            #current journey
            journey_list=nodemap_journey(current_role,nodemap_data)
            action_list=[]
            milestone_details = next((item for item in nodemap_data if item["milestone_id"] == milestone_id), None)
            milestone_data={"milestone_id":milestone_details["milestone_id"],"title":milestone_details["title"]}
            actions=milestone_details["actions"]
            cost_data = Cost_Details.find_one({'nodemap_id': id})
            for action in actions:
                act_id=action["action_id"]
                title=action["title"]
                act_data={"action_id":act_id,"title":title}
                action_list.append(act_data)
            mile_data={"milestones":milestone_data,"actions":action_list}
           
            matching_list=[]
            for i in action_data:
                action_id=i["action_id"]
                new_title=i["title"]
                result,cost=edit_actions_gpt_update(journey_list,new_title,mile_data,action_id)
                numeric_value = float(cost.split('$')[1])
                validate_action_cost={"mile_id":milestone_id,
                                                  "action_id":action_id,
                                       "validate_title_cost":cost,
                                     "created_on":datetime.now()}
                cost_data["variable_costs"]["edit_actions"]["edit_action_cost"].append(validate_action_cost)
                total_cost=cost_data["variable_costs"]["edit_actions"]["total_cost"]          
                if total_cost=="0":
                    cost_data["variable_costs"]["edit_actions"]["total_cost"]=cost
                else:
                    value=float(total_cost.split('$')[1])+numeric_value
                    cost_data["variable_costs"]["edit_actions"]["total_cost"]=f"${str(value)}"
                if cost_data["fixed_variable_sum"]=="0":
                                cost_data["fixed_variable_sum"]=cost
                else:
                    fixed_cost=cost_data["fixed_variable_sum"]
                    fixed_value=float(fixed_cost.split('$')[1])+numeric_value
                    cost_data["fixed_variable_sum"]=f"${str(fixed_value)}"
                    cost_data["updated_on"]=datetime.now()
                Cost_Details.update_one({'nodemap_id': id}, {'$set': cost_data})            
                response={"milestone_id":milestone_id,
                          "action_id":action_id,
                            "title":new_title,
                            "matching":result} 
                                
                            
                matching_list.append(response)
                            
            return Response({"response": matching_list},status=status.HTTP_200_OK)   
                                
            
        except json.JSONDecodeError:
            return Response({"message":"Please try again"}, status=status.HTTP_400_BAD_REQUEST)
        except ServiceUnavailableError:
            return Response({"message":"The server is overloaded or not ready yet"}, status=status.HTTP_400_BAD_REQUEST)                                 
        except RateLimitError: 
            return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#update action

class Edit_Action_View(APIView):
     def patch(self, request,id):
        try:
            request_body = request.body
            data = json.loads(request_body)
            action_data=data["action_data"]
            milestone_id=action_data[0]["milestone_id"]
            nodemap = dashboard_data.find_one({'_id': ObjectId(id)})
            if not nodemap:
                return Response({"message": "nodemap not found"}, status=status.HTTP_400_BAD_REQUEST)
            
            mile_obj = dashboard_data.find_one({ "milestones": { '$elemMatch': { "milestone_id": milestone_id } }})
            if not mile_obj:
                return Response({"message": "Invalid Milestone ID"}, status=status.HTTP_400_BAD_REQUEST)
            nodemap_data=nodemap["milestones"]
            milestone_details = next((item for item in nodemap_data if item["milestone_id"] == milestone_id), None)
            actions=milestone_details["actions"]
            for i in action_data:
                action_id=i["action_id"]
                # Find the milestone you want to update by its milestone_id
                for action in actions:
                    if action["action_id"]==int(action_id):
                        if "title" in i:
                            title=i["title"]
                            action["title"]=title
                        if "status" in i:
                            status_data=i["status"]
                            action["status"]=status_data
                        if "start_date" in i:
                            start_date=i["start_date"]
                            end_date=i["end_date"]
                            action["start_date"]=convert_date(start_date)
                            action["end_date"]=convert_date(end_date)
                            days=days_between(action["start_date"],action["end_date"])
                            action["duration"]=f"{days} days"

                        action["updated_on"] = datetime.now()
            if milestone_details["type"] != "targeted_role":
                if  "enablers" in milestone_details:
                    mile_progress=milestone_progress(milestone_details["actions"],milestone_details["enablers"])
                else:
                    mile_progress=milestone_progress(milestone_details["actions"],[])
                milestone_details["progress"]=mile_progress
                milestone_details["updated_on"]=datetime.now()
                if milestone_details["progress"]==100 :
                    northstar_progress=north_star_progress(nodemap["milestones"])
                    mile_data=nodemap["milestones"][-1]
                    mile_progress=milestone_progress(mile_data["actions"],mile_data["enablers"])
                    n_progress=(100/len(nodemap["milestones"]))*(mile_progress/100)
                    if  isinstance(n_progress,float):
                       nstar_progress=round(n_progress, 2)
                    if isinstance(n_progress,int):
                       nstar_progress=n_progress
                    mile_data["progress"]=northstar_progress+nstar_progress
                    mile_data["updated_on"]=datetime.now()
            if milestone_details["type"] == "targeted_role":
                northstar_progress=north_star_progress(nodemap["milestones"])
                mile_progress=milestone_progress(milestone_details["actions"],milestone_details["enablers"])
                n_progress=(100/len(nodemap["milestones"]))*(mile_progress/100)
                if isinstance(n_progress,float):
                   nstar_progress=round(n_progress, 2)
                if isinstance(n_progress,int):
                   nstar_progress=n_progress
                milestone_details["progress"]=northstar_progress+nstar_progress
                milestone_details["updated_on"]=datetime.now()
            dashboard_data.update_one({'_id': ObjectId(id)}, {'$set': nodemap})
            return Response({"message": "updated sucessfully"},status=status.HTTP_200_OK)

        except json.JSONDecodeError:
            return Response({"message":"Please try again"}, status=status.HTTP_400_BAD_REQUEST)
        except ServiceUnavailableError:
            return Response({"message":"The server is overloaded or not ready yet"}, status=status.HTTP_400_BAD_REQUEST)      
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

'''Validate Intermediate'''
class ValidateIntermediate(APIView):
    def post(self,request):
        try:
            request_data=request.body
            data=json.loads(request_data)
            id = data.pop('nodemap_id')
            new_title = data['title']
            milestone_id=data.pop('milestone_id')
            dashboard_obj = dashboard_data.find_one({"_id": ObjectId(id)})
            if not dashboard_obj:
                return Response({"message": "Nodemap data not found"}, status=status.HTTP_400_BAD_REQUEST)
            
            mile_obj = dashboard_data.find_one({ "milestones": { '$elemMatch': { "milestone_id": milestone_id } }})
            if not mile_obj:
                return Response({"message": "Invalid Milestone ID"}, status=status.HTTP_400_BAD_REQUEST)
            
            user_id = dashboard_obj['user_id']
            # print(user_id)
            nodemap = dashboard_obj.get("milestones",[])
            for inter in nodemap:
                if inter.get('milestone_id') == milestone_id:
                    old_title = inter['title']
            questionnaire_obj = users_registration.find_one({"_id": ObjectId(user_id)})
            if not questionnaire_obj:
                return Response({"message": "Questionnaire data found"}, status=status.HTTP_400_BAD_REQUEST)
            onboarding = questionnaire_obj.get('questionnaire',{})
            current_role = onboarding['career_runway_role_description']
            new_journey_structure = nodemap_journey(current_role,nodemap)
            # print(new_journey_structure)
            response, cost = intermediate_validate(milestone_id,new_journey_structure,old_title,new_title)
            result = {
                "title": data['title'],
                "matching": response
            }
            cost_data = Cost_Details.find_one({'nodemap_id': id})
            numeric_value = float(cost.split('$')[1])
            validate_milestone_cost={"mile_id":milestone_id,
                                     "validate_title_cost":cost,
                                     "generate_milestone_cost":"",
                                     "created_on":datetime.now()}
            
            cost_data["variable_costs"]["edit_intermediate"]["edit_intermediate_cost"].append(validate_milestone_cost)
            total_cost=cost_data["variable_costs"]["edit_intermediate"]  
         
            if total_cost["total_cost"] =="0":
                total_cost["total_cost"]=cost
                total_cost["updated_on"]=datetime.now()
            else:
                total_cost_data=cost_data["variable_costs"]["edit_intermediate"]["total_cost"]
                value=float(total_cost_data.split('$')[1])+numeric_value
                total_cost["total_cost"] =f"${str(value)}"
                total_cost["updated_on"]=datetime.now()
            if cost_data["fixed_variable_sum"]=="0":
                cost_data["fixed_variable_sum"]=cost
            else:
                fixed_cost=cost_data["fixed_variable_sum"]
                value=float(fixed_cost.split('$')[1])+numeric_value
                cost_data["fixed_variable_sum"]=f"${str(value)}"

            Cost_Details.update_one({'nodemap_id': id}, {'$set': cost_data})
            return Response({"response": result}, status=status.HTTP_200_OK)
        except json.JSONDecodeError:
            return Response({"message":"Please try again"}, status=status.HTTP_400_BAD_REQUEST)
        except ServiceUnavailableError:
            return Response({"message":"The server is overloaded or not ready yet"}, status=status.HTTP_400_BAD_REQUEST) 
        except RateLimitError: 
            return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)       
        except Exception as e:
            return Response({"message": "An error occured","error" :str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            


'''Edit Intermediate'''
class EditIntermediate(APIView):
    def patch(self,request,id):
        try:
            request_data=request.body
            data=json.loads(request_data)
            milestone_id=data.pop('milestone_id')
            if 'reason' in data:
                reason=data.pop('reason')
            else:
                reason = None
            update_timeline=data.pop('update_timeline')
            generate_milestone=data.pop('generate_milestone')
            dashboard_obj = dashboard_data.find_one({"_id": ObjectId(id)})
            if not dashboard_obj:
                return Response({"message": "No data found"}, status=status.HTTP_400_BAD_REQUEST)
            
            mile_obj = dashboard_data.find_one({ "milestones": { '$elemMatch': { "milestone_id": milestone_id } }})
            if not mile_obj:
                return Response({"message": "Invalid Milestone ID"}, status=status.HTTP_400_BAD_REQUEST)
            
            intermediate = dashboard_obj.get("milestones",[])
            rename_intermediate = None 
            user_id = dashboard_obj['user_id']
        
            for inter in intermediate:
                if inter.get('milestone_id') == milestone_id:
                    rename_intermediate = inter
                    break
            if rename_intermediate:
                if 'role_details' in data:
                    role_details=data.pop('role_details')
                    rename_intermediate['intermediate_role'].update(role_details)
                if "start_date" in data:
                    start_date_str = data['start_date']
                    data['start_date'] = convert_date(start_date_str)
                if "end_date" in data:
                    end_date_str = data['end_date']
                    data['end_date'] = convert_date(end_date_str)
                date_diff = date_difference(start_date_str,end_date_str)
                data['timeline'] = f"{date_diff} day(s)"
                rename_intermediate.update(data)
                rename_intermediate["updated_on"]=datetime.now()
            dashboard_data.update_one({'_id':ObjectId(id)},{'$set': dashboard_obj})

            if str(generate_milestone).lower() == "yes":
                domain = request.META['HTTP_HOST']
                if domain=="127.0.0.1:8000":    
                    path_1 = './Milestones Bucket_2.xlsx'
                else:    
                    path_1 = '/var/www/html/Backend/Milestones Bucket_2.xlsx'
                index = []
                milestone_duration_days = 0
                for idx,inter in enumerate(intermediate):
                    if inter['type'] == 'intermediate_role':
                        index.append({"index" :idx,"milestone_id": inter['milestone_id'],"title":inter['title'],"rank":inter['intermediate_role']['rank']})
                title_list = []
                # print("journey_list",index)
                for idx,data in enumerate(index):
                    if data['milestone_id'] == milestone_id:
                        new_title = data['title']
                        new_title_rank = data['rank']
                        matched_index = idx
                    
                if matched_index == 0: # Case 1: When user edits IR1(m1,m2,IR1,m3,m4,IR2,m5,m6,NS)
                    get_user_data = users_registration.find_one({'_id':ObjectId(user_id)})
                    if not get_user_data:
                        return Response({"message": "No questionnaire data found"}, status=status.HTTP_400_BAD_REQUEST)
                    current_role = get_user_data['questionnaire']['career_runway_role_description']['role']
                    index_1 = index[matched_index]['index']

                    for mile_idx,milestone in enumerate(intermediate[:index_1+1]):
                        timeline_sum = int(str(milestone['timeline']).split(' ')[0])
                        milestone_duration_days = milestone_duration_days + timeline_sum
                        # print("mile duration",milestone_duration_days)
                        actions_list = []
                        for actions in milestone['actions']:
                            if actions['status'] != 0:
                                actions_list.append(actions['title'])
                        if actions_list:
                            completed_milestones = {'milestone_title': milestone['title'],'actions': actions_list}
                            title_list.append(completed_milestones)
                            last_mile_end_date = milestone['end_date']
                            current_date = datetime.now()
                            if last_mile_end_date < current_date - timedelta(days=1):
                                last_mile_end_date = current_date
                            else:
                                last_mile_end_date = milestone['end_date'] + timedelta(days = 1)
                            mile_from_index = mile_idx
                            if milestone['type'] == 'intermediate_role':
                                for act in milestone['actions']:
                                    act['status'] = 0
                                flag = 0
                                break 
                   
                    if title_list: # When user has made some progress in any one of the action under a milestone
                        last_mile_date = last_mile_end_date
                        response, cost = generate_milestone_actions(title_list,current_role,new_title_rank,new_title,milestone_duration_days,path_1)
                        restructured_data = edit_inter_restructure(response['milestones'],last_mile_date)
                        if flag == 0:
                            milestones = intermediate[:mile_from_index] + restructured_data + intermediate[index_1:]
                        else:
                            milestones = intermediate[:mile_from_index+1] + restructured_data + intermediate[index_1:]
                    else: # When user has not made any progress in any action under a milestone
                        last_mile_date = datetime.now()
                        response, cost = generate_milestone_actions(title_list,current_role,new_title_rank,new_title,milestone_duration_days,path_1)
                        restructured_data = edit_inter_restructure(response['milestones'],last_mile_date)
                        milestones = restructured_data + intermediate[index_1:]
            
                elif matched_index > 0 and matched_index < len(index): # Case 2: When user edits IR2(m1,m2,IR1,m3,m4,IR2,m5,m6,NS)
                    from_index_2 = index[matched_index-1]['index']
                    current_role = index[matched_index-1]['title']
                    to_index_2 = index[matched_index]['index']
                    mile_from_index = from_index_2
                    # print(from_index_2)
                    # print(to_index_2)
                    for mile_idx,milestone in enumerate(intermediate[from_index_2+1:to_index_2+1]):
                        timeline_sum = int(str(milestone['timeline']).split(' ')[0])
                        milestone_duration_days = milestone_duration_days + timeline_sum
                        # print("mile duration",milestone_duration_days)
                        actions_list = []
                        for actions in milestone['actions']:
                            if actions['status'] != 0:
                                actions_list.append(actions['title'])
                        if actions_list:
                            completed_milestones = {'milestone_title': milestone['title'],'actions': actions_list}
                            title_list.append(completed_milestones)
                            last_mile_end_date = milestone['end_date']
                            current_date = datetime.now()
                            if last_mile_end_date < current_date - timedelta(days=1):
                                last_mile_end_date = current_date
                            else:
                                last_mile_end_date = milestone['end_date'] + timedelta(days = 1)
                            mile_from_index = mile_from_index + 1
                            if milestone['type'] == 'intermediate_role':
                                for act in milestone['actions']:
                                    act['status'] = 0
                                flag = 0
                                break  

                    if title_list:
                        last_mile_date = last_mile_end_date
                        response, cost = generate_milestone_actions(title_list,current_role,new_title_rank,new_title,milestone_duration_days,path_1)
                        restructured_data = edit_inter_restructure(response['milestones'],last_mile_date)
                        if flag == 0:
                            milestones = intermediate[:mile_from_index-2] + restructured_data + intermediate[to_index_2:]
                        else:
                            milestones = intermediate[:mile_from_index+1] + restructured_data + intermediate[to_index_2:]
                    else:
                        last_mile_date = datetime.now()
                        response, cost = generate_milestone_actions(title_list,current_role,new_title_rank,new_title,milestone_duration_days,path_1)
                        restructured_data = edit_inter_restructure(response['milestones'],last_mile_date)
                        milestones = intermediate[:from_index_2+1] + restructured_data + intermediate[to_index_2:]
                else:
                    return Response({"message": "No data found"}, status=status.HTTP_400_BAD_REQUEST) 
                dashboard_obj['milestones'] = milestones
                ns_progress=north_star_progress(dashboard_obj["milestones"])
                mile_data=dashboard_obj["milestones"][-1]
                mile_data['progress'] = ns_progress
                dashboard_data.replace_one({"_id": ObjectId(id)}, dashboard_obj)
                cost_data = Cost_Details.find_one({'nodemap_id': id})
                numeric_value = float(cost.split('$')[1]) 
                cost_details=cost_data["variable_costs"]["edit_intermediate"]["edit_intermediate_cost"][-1]
                cost_details["generate_milestone_cost"]=cost
                cost_details["updated_on"]=datetime.now()
                total_cost=cost_data["variable_costs"]["edit_intermediate"]          
                total_cost_data=cost_data["variable_costs"]["edit_intermediate"]["total_cost"]
                value=float(total_cost_data.split('$')[1])+numeric_value
                total_cost["total_cost"]=f"${str(value)}"
                total_cost["updated_on"]=datetime.now()
                if cost_data["fixed_variable_sum"]=="0":
                    cost_data["fixed_variable_sum"]=cost
                else:
                    fixed_cost=cost_data["fixed_variable_sum"]
                    value=float(fixed_cost.split('$')[1])+numeric_value
                    cost_data["fixed_variable_sum"]=f"${str(value)}"
                Cost_Details.update_one({'nodemap_id': id}, {'$set': cost_data}) 
            if update_timeline == "yes":
                index=get_index(intermediate,milestone_id)
                index_data=index+1
                mile_data=update_milestone_timeline(intermediate,index_data)
                dashboard_obj["milestones"]=mile_data
                dashboard_data.update_one({'_id':ObjectId(id)},{'$set': dashboard_obj})
            if reason != None: 
                reason_data = Reason.find_one({'nodemap_id': id})
                if reason_data:
                    d={"mile_id":milestone_id,
                    "reason":reason,
                        "created_on":datetime.now()
                    }
                    reason_data["save_reason"]["edit_intermediate"].append(d)
                    Reason.update_one({'nodemap_id': id}, {'$set': reason_data})
                else:
                    d={
                        "user_id":user_id,
                        "nodemap_id": id,
                        "save_reason": {
                    "edit_intermediate": [{
                            "mile_id": milestone_id,
                            "reason":reason,
                            "created_on":datetime.now()

                        }],
                        "add_milestone":[],
                        "edit_north_star":[],
                        "add_intermediate":[],
                        "edit_milestone":[]}}
                    Reason.insert_one(d).inserted_id           
            return Response({"message": "successfully updated"}, status=status.HTTP_200_OK)
        except json.JSONDecodeError:
            return Response({"message":"Please try again"}, status=status.HTTP_400_BAD_REQUEST)
        except ServiceUnavailableError:
            return Response({"message":"The server is overloaded or not ready yet"}, status=status.HTTP_400_BAD_REQUEST) 
        except RateLimitError: 
            return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)       
        except Exception as e:
            return Response({"message": "An error occured","error" :str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

'''Get Entry to place under'''
class GetEntryToPlace(APIView):
    def get(self, request, id):
        try:
            nodemap_obj = dashboard_data.find_one({'_id':ObjectId(id)})
            if not nodemap_obj:
                return Response({"message": "No data found"}, status=status.HTTP_400_BAD_REQUEST)
            user_id = nodemap_obj['user_id']
            place_under = []
            milestones = nodemap_obj.get("milestones", [])
            get_current = users_registration.find_one({'_id':ObjectId(user_id)})
            if not get_current:
                return Response({"message":"Questionnaire data not found"})
            current_role = get_current['questionnaire']['career_runway_role_description']['role']
            mile_len = len(milestones)
            target_data = milestones[mile_len - 1]
            target_progress = target_data['progress']
            if int(target_progress) == 100:
                return Response({"message": "You have successfully completed your nodemap"})
            elem_match = dashboard_data.find_one({
                '$and': [ 
                {"milestones": { '$elemMatch': { "type": "intermediate_role" }}},
                {"_id": ObjectId(id)}
                ]})
            if elem_match is None:
                next_id = target_data['milestone_id']
                next_title = target_data['title']
                append_current = {"current_title" :current_role,
                 "current_id" :"current123",
                 "next_id":next_id,
                 "next_title":next_title}
                place_under.append(append_current)
                return Response({"response": place_under}, status=status.HTTP_200_OK)
            i = 0
            for index, milestone in enumerate(milestones):
                if milestone.get('progress', 0) == 100 and milestone.get('type') in ["intermediate_role", "targeted_role"]:
                    i=i+1
                    for next_index in range(index + 1, len(milestones)):
                        if milestones[next_index].get('type') in ["intermediate_role", "targeted_role"]:
                            place_under_0 = {
                                "current_id": milestone['milestone_id'],
                                "current_title": milestone['title'],
                                "next_id": milestones[next_index]['milestone_id'],
                                "next_title": milestones[next_index]['title'],
                            }
                            break
                if milestone.get('progress', 0) != 100 and milestone.get('type') in ["intermediate_role", "targeted_role"]:
                    for next_index in range(index + 1, len(milestones)):
                        if milestones[next_index].get('type') in ["intermediate_role", "targeted_role"]:
                            place_under.append({
                                "current_id": milestone['milestone_id'],
                                "current_title": milestone['title'],
                                "next_id": milestones[next_index]['milestone_id'],
                                "next_title": milestones[next_index]['title'],
                            })
                            break
            if i==0:
                next_id = place_under[0]['current_id']
                next_title = place_under[0]['current_title']
                append_current = {"current_title" :current_role,
                "current_id" :"current123",
                "next_id":next_id,
                "next_title":next_title}
                place_under.insert(0,append_current)
            else:
                # target_progress = target_data['progress']
                # if place_under == [] and int(target_progress) == 1:
                #     return Response({"message": "You have successfully completed your nodemap"})
                place_under.insert(0,place_under_0)
            return Response({"response": place_under}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": "An error occured","error" :str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
'''Add Intermediate Title Validate'''
class Validate_AddIntermediate(APIView):
    def post(self,request):
        try:
            request_data=request.body
            data=json.loads(request_data)
            id = data.pop('nodemap_id')
            new_title = data['title']
            dashboard_obj = dashboard_data.find_one({"_id": ObjectId(id)})
            if not dashboard_obj:
                return Response({"message": "Nodemap data not found"}, status=status.HTTP_400_BAD_REQUEST)
            
            user_id = dashboard_obj['user_id']
            nodemap = dashboard_obj.get("milestones",[])
            questionnaire_obj = users_registration.find_one({"_id": ObjectId(user_id)})
            if not questionnaire_obj:
                return Response({"message": "Questionnaire data found"}, status=status.HTTP_400_BAD_REQUEST)
            onboarding = questionnaire_obj.get('questionnaire',{})
            current_role = onboarding['career_runway_role_description']
            new_journey_structure = nodemap_journey(current_role,nodemap)
            # print(new_journey_structure)
            response, cost = validate_addintermediate_title(new_journey_structure,new_title)
            result = {
                "title": data['title'],
                "matching": response
            }
            cost_data = Cost_Details.find_one({'nodemap_id': id})
            numeric_value = float(cost.split('$')[1])
            validate_milestone_cost={"mile_id":"",
                                     "validate_title_cost":cost,
                                     "generate_milestone_cost":"",
                                     "created_on":datetime.now()}
            
            cost_data["variable_costs"]["add_intermediate"]["add_intermediate_cost"].append(validate_milestone_cost)
            total_cost=cost_data["variable_costs"]["add_intermediate"]  
            #print(total_cost)       
            if total_cost["total_cost"] =="0":
                total_cost["total_cost"]=cost
                total_cost["updated_on"]=datetime.now()
            else:
                total_cost_data=cost_data["variable_costs"]["add_intermediate"]["total_cost"]
                value=float(total_cost_data.split('$')[1])+numeric_value
                total_cost["total_cost"] =f"${str(value)}"
                total_cost["updated_on"]=datetime.now()
            if cost_data["fixed_variable_sum"]=="0":
                cost_data["fixed_variable_sum"]=cost
            else:
                fixed_cost=cost_data["fixed_variable_sum"]
                value=float(fixed_cost.split('$')[1])+numeric_value
                cost_data["fixed_variable_sum"]=f"${str(value)}"

            Cost_Details.update_one({'nodemap_id': id}, {'$set': cost_data})
            return Response({"response": result}, status=status.HTTP_200_OK)
        except json.JSONDecodeError:
            return Response({"message":"Please try again"}, status=status.HTTP_400_BAD_REQUEST)
        except ServiceUnavailableError:
            return Response({"message":"The server is overloaded or not ready yet"}, status=status.HTTP_400_BAD_REQUEST) 
        except RateLimitError: 
            return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)       
        except Exception as e:
            return Response({"message": "An error occured","error" :str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

'''Add Intermediate Role'''
class Add_Intermediate(APIView):
    def post(self,request):
        try: 
            request_data=request.body
            data=json.loads(request_data)
            id = data.pop('nodemap_id')
            if 'reason' in data:
                reason = data.pop('reason')
            update_timeline = data.pop('update_timeline')
            nodemap_obj = dashboard_data.find_one({'_id':ObjectId(id)})
            user_id = nodemap_obj['user_id']
            if not nodemap_obj:
                return Response({"message": "No data found"}, status=status.HTTP_400_BAD_REQUEST)
            milestones = nodemap_obj.get("milestones", [])
            start_date = data['start_date']
            end_date = data['start_date']

            current_id = data['place_between']['current_id']
            if current_id != 'current123':
                for mile in milestones: 
                    if mile['milestone_id'] == current_id:
                        update_mile_progress = mile['progress']
                        break
            next_id = data['place_between']['next_id']

            current_title = data['place_between']['current_title']
            next_title = data['place_between']['next_title']

            new_title = data['title']
            days_diff = date_difference(start_date,end_date)
            total_timeline,current_id_start_date = calculate_timeline(milestones,current_id,next_id,days_diff)
            domain = request.META['HTTP_HOST']
            if domain=="127.0.0.1:8000":    
                path_1 = './Milestones Bucket_2.xlsx'
                path_2 = './Milestones Bucket_3.xlsx'
            else:    
                path_1 = '/var/www/html/Backend/Milestones Bucket_2.xlsx'
                path_2 = '/var/www/html/Backend/Milestones Bucket_3.xlsx'

            current_type,next_type,inter_list,target_list = find_mile_type(milestones,current_id,next_id)
          
            new_type = "intermediate_role"
            new_type_role_details = data['role_details']
            new_title_rank = data['role_details']['rank']
            if len(inter_list) == 2: # add intermediate between two intermediate
                inter_list.insert(1,new_type_role_details)
            elif len(inter_list) == 1 and current_type == 'milestone': # add intermediate between current and intermediate
                inter_list.insert(0,new_type_role_details)
            else:             #add intermediate between current and NS or between intermediate and NS
                inter_list.append(new_type_role_details)
            # print(inter_list)
            
            new_data, cost = add_intermediate(current_title,current_type,new_title,new_type,next_title,next_type,total_timeline,path_1,path_2,new_title_rank) 
            structured_add_intermediate = new_nodemap(new_data['milestones'],inter_list,target_list,current_id_start_date)
            if str(structured_add_intermediate[0]['type']).lower() != 'milestone':
                structured_add_intermediate[0]['progress'] = update_mile_progress
            if str(structured_add_intermediate[0]['type']).lower() != 'milestone' and str(structured_add_intermediate[-1]['type']).lower() != 'milestone':
                for add_inter in structured_add_intermediate[1:-2]:
                    if add_inter['type'] == 'intermediate_role':
                        new_mile_id = add_inter['milestone_id']
                        break
            else:
                for add_inter in structured_add_intermediate[0:-2]:
                    if add_inter['type'] == 'intermediate_role':
                        new_mile_id = add_inter['milestone_id']
                        break 
            new_milestones = append_new_intermediate(milestones,current_id,next_id,structured_add_intermediate)
            nodemap_obj["milestones"] = new_milestones
            if update_timeline == "yes":
                last_mile_id = structured_add_intermediate[len(structured_add_intermediate) - 1]['milestone_id']
                # print(last_mile_id)
                index=get_index(new_milestones,last_mile_id)
                index_data=index+1
                if index_data == len(new_milestones):
                    nodemap_obj["milestones"] = new_milestones
                else:
                    mile_data=update_milestone_timeline(new_milestones,index_data)
                    nodemap_obj["milestones"]=mile_data
            
            ns_progress=north_star_progress(nodemap_obj["milestones"])
            mile_data=nodemap_obj["milestones"][-1]
            mile_data['progress'] = ns_progress
            dashboard_data.replace_one({"_id": ObjectId(id)}, nodemap_obj)
            cost_data = Cost_Details.find_one({'nodemap_id': id})
            numeric_value = float(cost.split('$')[1]) 
            cost_details=cost_data["variable_costs"]["add_intermediate"]["add_intermediate_cost"][-1]
            cost_details["mile_id"]= str(new_mile_id)
            cost_details["generate_milestone_cost"]=cost
            cost_details["updated_on"]=datetime.now()
            total_cost=cost_data["variable_costs"]["add_intermediate"]          
            total_cost_data=cost_data["variable_costs"]["add_intermediate"]["total_cost"]
            value=float(total_cost_data.split('$')[1])+numeric_value
            total_cost["total_cost"]=f"${str(value)}"
            total_cost["updated_on"]=datetime.now()
            if cost_data["fixed_variable_sum"]=="0":
                cost_data["fixed_variable_sum"]=cost
            else:
                fixed_cost=cost_data["fixed_variable_sum"]
                value=float(fixed_cost.split('$')[1])+numeric_value
                cost_data["fixed_variable_sum"]=f"${str(value)}"
            Cost_Details.update_one({'nodemap_id': id}, {'$set': cost_data})

            reason_data = Reason.find_one({'nodemap_id': id})
            if reason_data:
                d={"mile_id":str(new_mile_id),
                   "reason":reason,
                    "created_on":datetime.now()
                   }
                reason_data["save_reason"]["add_intermediate"].append(d)
                Reason.update_one({'nodemap_id': id}, {'$set': reason_data})
            else:
                d={
                    "user_id":user_id,
                    "nodemap_id": id,
                    "save_reason": {
                   "add_intermediate": [{
                        "mile_id": str(new_mile_id),
                        "reason":reason,
                        "created_on":datetime.now()

                      }],
                      "add_milestone":[],
                      "edit_intermediate":[],
                      "edit_milestone":[],
                      "edit_north_star":[]}}
                Reason.insert_one(d).inserted_id
            return Response({"message":"Successfully added your new intermediate role to the nodemap"},status=status.HTTP_200_OK)  
        except json.JSONDecodeError:
            return Response({"message":"Please try again"}, status=status.HTTP_400_BAD_REQUEST)
        except ServiceUnavailableError:
            return Response({"message":"The server is overloaded or not ready yet"}, status=status.HTTP_400_BAD_REQUEST)      
        except RateLimitError: 
            return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)       
        except Exception as e:
            return Response({"message": "An error occured","error" :str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#Add Actions
#validate Action title

class Validate_Action_title_View(APIView):
    def post(self, request):
        try:
            request_body = request.body
            data = json.loads(request_body)
            id=data["id"]
            action_data=data["action_data"]
            nodemap = dashboard_data.find_one({'_id': ObjectId(id)})

            if not nodemap:
                return Response({"message": "nodemap not found"}, status=status.HTTP_400_BAD_REQUEST)
            
            milestone_id=action_data[0]["milestone_id"]
            mile_obj = dashboard_data.find_one({ "milestones": { '$elemMatch': { "milestone_id": milestone_id } }})
            if not mile_obj:
                return Response({"message": "Invalid Milestone ID"}, status=status.HTTP_400_BAD_REQUEST)
            
            user_id=nodemap["user_id"]
            user_data = users_registration.find_one({'_id': ObjectId(user_id)})
            current_role = user_data['questionnaire']['career_runway_role_description']
            nodemap=nodemap["milestones"]
            journey_list=nodemap_journey(current_role,nodemap)
            matching_list=[]
            body_len=len(action_data)
            cost_data = Cost_Details.find_one({'nodemap_id': id})
          
            for milestone in nodemap:
                    if milestone["milestone_id"] == milestone_id:
                        milestone_data={"milestone_id":milestone["milestone_id"],"title":milestone["title"]}
                        actions=milestone["actions"]
                        limit=len(actions)
                        l=5-limit
                        # if limit>5:
                        #     return Response({"message": "Add action limit is more "})
                        if l==0:
                            return Response({"message": "You have 5 action now you can not add more action"},status=status.HTTP_400_BAD_REQUEST)
                        if limit+body_len>5:
                            return Response({"message": f"you can add {l} action"},status=status.HTTP_400_BAD_REQUEST)
                        
                        for i in action_data:
                            new_title=i["title"]
                            # milestone_id=i["milestone_id"]
                            result,cost=add_actions_gpt(journey_list,new_title,milestone_data,milestone_id)
                            numeric_value = float(cost.split('$')[1])
                            validate_action_cost={"mile_id":milestone_id,
                                                  "action_id":"",
                                       "validate_title_cost":cost,
                                     "add_action_cost":"",
                                     "created_on":datetime.now()}
                            cost_data["variable_costs"]["add_actions"]["add_action_cost"].append(validate_action_cost)
                            total_cost=cost_data["variable_costs"]["add_actions"]["total_cost"]          
                            if total_cost=="0":
                                cost_data["variable_costs"]["add_actions"]["total_cost"]=cost
                            else:
                                value=float(total_cost.split('$')[1])+numeric_value
                                cost_data["variable_costs"]["add_actions"]["total_cost"]=f"${str(value)}"
                            if cost_data["fixed_variable_sum"]=="0":
                                cost_data["fixed_variable_sum"]=cost
                            else:
                                fixed_cost=cost_data["fixed_variable_sum"]
                                fixed_value=float(fixed_cost.split('$')[1])+numeric_value
                                cost_data["fixed_variable_sum"]=f"${str(fixed_value)}"
                                cost_data["updated_on"]=datetime.now()
                            Cost_Details.update_one({'nodemap_id': id}, {'$set': cost_data})
                            response={"milestone_id":milestone_id,
                                          "title":new_title,
                                          "matching":result} 
                                
                            
                            matching_list.append(response)
                            
            return Response({"response": matching_list},status=status.HTTP_200_OK)
        except json.JSONDecodeError:
            return Response({"message":"Please try again"}, status=status.HTTP_400_BAD_REQUEST)
        except ServiceUnavailableError:
            return Response({"message":"The server is overloaded or not ready yet"}, status=status.HTTP_400_BAD_REQUEST)      
        except RateLimitError: 
            return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



#add action
class Add_Action_View(APIView):
     def post(self, request):
        try:
            request_body = request.body
            body= json.loads(request_body)
            id=body["id"]
            action_data=body["action_data"]
            length=len(action_data)
            nodemap = dashboard_data.find_one({'_id': ObjectId(id)})

            if not nodemap:
                return Response({"message": "nodemap not found"}, status=status.HTTP_400_BAD_REQUEST)
            milestone_id=action_data[0]["milestone_id"]
            mile_obj = dashboard_data.find_one({ "milestones": { '$elemMatch': { "milestone_id": milestone_id } }})
            if not mile_obj:
                return Response({"message": "Invalid Milestone ID"}, status=status.HTTP_400_BAD_REQUEST)
            
            user_id=nodemap["user_id"]
            user_data = users_registration.find_one({'_id': ObjectId(user_id)})
            current_role = user_data['questionnaire']['career_runway_role_description']
            nodemap_data=nodemap["milestones"]
            journey_list=nodemap_journey(current_role,nodemap_data)
            milestone_details = next((item for item in nodemap_data if item["milestone_id"] == milestone_id), None)
            milestone_data={"milestone_id":milestone_details["milestone_id"],"title":milestone_details["title"]}
            cost_data = Cost_Details.find_one({'nodemap_id': id})
            add_action_length=cost_data["variable_costs"]["add_actions"]["add_action_cost"][-length:]
            for i in action_data:
                index_data=action_data.index(i)
                
                title=i["title"]
                start_date=convert_date(i["start_date"])
                end_date=convert_date(i["end_date"])
                days=days_between(start_date,end_date)
                status_data=i["status"]
                result,cost=generate_description_actions_gpt(journey_list,title,milestone_data)
                des=result["description"]
                actions=milestone_details["actions"]
                length=max([ach.get('action_id', 0) for ach in actions], default=0)
                max_id=length+1
                numeric_value = float(cost.split('$')[1])
                # add_action_length=cost_data["variable_costs"]["add_actions"]["add_action_cost"][-length:]
                # print(add_action_length)
                add_action_length[index_data]["action_id"]=max_id
                add_action_length[index_data]["add_action_cost"]=cost
                add_action_length[index_data]["updated_on"]=datetime.now()
                total_cost=cost_data["variable_costs"]["add_actions"]["total_cost"] 
                value=float(total_cost.split('$')[1])+numeric_value
                cost_data["variable_costs"]["add_actions"]["total_cost"]=f"${str(value)}"
                fixed_cost=cost_data["fixed_variable_sum"]
                fixed_value=float(fixed_cost.split('$')[1])+numeric_value
                cost_data["fixed_variable_sum"]=f"${str(fixed_value)}"
                cost_data["updated_on"]=datetime.now()
                Cost_Details.update_one({'nodemap_id': id}, {'$set': cost_data})
                actions_data={
                                        "action_id":max_id,
                                        "title":title,
                                        "description":des,
                                        "duration":f"{days} days",
                                        "start_date":start_date,
                                        "end_date":end_date,
                                        "status":status_data,
                                        "created_on":datetime.now(),
                                        "updated_on":datetime.now(),
                                    }
                actions.append(actions_data)
            if milestone_details["type"] != "targeted_role":
                if  "enablers" in milestone_details:
                    mile_progress=milestone_progress(milestone_details["actions"],milestone_details["enablers"])
                else:
                    mile_progress=milestone_progress(milestone_details["actions"],[])
                milestone_details["progress"]=mile_progress
                milestone_details["updated_on"]=datetime.now()
            if milestone_details["type"] == "targeted_role":
                northstar_progress=north_star_progress(nodemap["milestones"])
                mile_progress=milestone_progress(milestone_details["actions"],milestone_details["enablers"])
                n_progress=(100/len(nodemap["milestones"]))*(mile_progress/100)
                if isinstance(n_progress,float):
                   nstar_progress=round(n_progress, 2)
                if isinstance(n_progress,int):
                   nstar_progress=n_progress
                milestone_details["progress"]=northstar_progress+nstar_progress
                milestone_details["updated_on"]=datetime.now()

            dashboard_data.update_one({'_id': ObjectId(id)}, {'$set': nodemap})
            return Response({"message": " updated sucessfully"},status=status.HTTP_200_OK)

        except json.JSONDecodeError:
            return Response({"message":"Please try again"}, status=status.HTTP_400_BAD_REQUEST)
        except ServiceUnavailableError:
            return Response({"message":"The server is overloaded or not ready yet"}, status=status.HTTP_400_BAD_REQUEST)      
        except RateLimitError: 
            return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



#validate milestone title
class Validate_Milestone_title_View(APIView):
    def post(self, request):
        try:
            request_body = request.body
            data = json.loads(request_body)
            id=data["id"]
            milestone_id=data["milestone_id"]
            nodemap = dashboard_data.find_one({'_id': ObjectId(id)})

            if not nodemap:
                return Response({"message": "nodemap not found"}, status=status.HTTP_400_BAD_REQUEST)
            mile_obj = dashboard_data.find_one({ "milestones": { '$elemMatch': { "milestone_id": milestone_id } }})
            if not mile_obj:
                return Response({"message": "Invalid Milestone ID"}, status=status.HTTP_400_BAD_REQUEST)
            user_id=nodemap["user_id"]
            user_data = users_registration.find_one({'_id': ObjectId(user_id)})
            current_role = user_data['questionnaire']['career_runway_role_description']
            nodemap_data=nodemap["milestones"]
            journey_list=nodemap_journey(current_role,nodemap_data)
            milestone_details = next((item for item in nodemap_data if item["milestone_id"] == milestone_id), None)
            milestone_data={"milestone_id":milestone_details["milestone_id"],"title":milestone_details["title"]}
            reason = data["reason"]
            new_title = data["title"]        
          
            result,cost= edit_milestones_gpt(journey_list,new_title,milestone_data)
            cost_data = Cost_Details.find_one({'nodemap_id': id})
            # print(cost_data)
            numeric_value = float(cost.split('$')[1])
            validate_milestone_cost={"mile_id":milestone_id,
                                       "validate_title_cost":cost,
                                     "generate_action_cost":"",
                                     "created_on":datetime.now()}
            
            cost_data["variable_costs"]["edit_milestone"]["edit_milestone_cost"].append(validate_milestone_cost)
            total_cost=cost_data["variable_costs"]["edit_milestone"]         
            if total_cost["total_cost"]=="0":
                total_cost["total_cost"]=cost
                total_cost["updated_on"]=datetime.now()
            else:
                total_cost_details=cost_data["variable_costs"]["edit_milestone"]["total_cost"]
                value=float(total_cost_details.split('$')[1])+numeric_value
                total_cost["total_cost"]=f"${str(value)}"
                total_cost["updated_on"]=datetime.now()
            if cost_data["fixed_variable_sum"]=="0":
                cost_data["fixed_variable_sum"]=cost
            else:
                fixed_cost=cost_data["fixed_variable_sum"]
                value=float(fixed_cost.split('$')[1])+numeric_value
                cost_data["fixed_variable_sum"]=f"${str(value)}"
                cost_data["updated_on"]=datetime.now()

            Cost_Details.update_one({'nodemap_id': id}, {'$set': cost_data})
            if result=="yes":
                return Response({"milestone_id":milestone_id,"matching": result},status=status.HTTP_200_OK)   
            return Response({"milestone_id":milestone_id,"matching": result},status=status.HTTP_200_OK)
            
        
        except json.JSONDecodeError:
            return Response({"message":"Please try again"}, status=status.HTTP_400_BAD_REQUEST)
        except ServiceUnavailableError:
            return Response({"message":"The server is overloaded or not ready yet"}, status=status.HTTP_400_BAD_REQUEST)      
        except RateLimitError: 
            return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



#update milestone
class Update_Milestone_View(APIView):
    def patch(self, request,id):
        try:
            request_body = request.body
            data = json.loads(request_body)
            nodemap = dashboard_data.find_one({'_id': ObjectId(id)})

            if not nodemap:
                return Response({"message": "nodemap not found"}, status=status.HTTP_400_BAD_REQUEST)
            milestone_id=data["milestone_id"]
            mile_obj = dashboard_data.find_one({ "milestones": { '$elemMatch': { "milestone_id": milestone_id } }})
            if not mile_obj:
                return Response({"message": "Invalid Milestone ID"}, status=status.HTTP_400_BAD_REQUEST)
            user_id=nodemap["user_id"]
            user_data = users_registration.find_one({'_id': ObjectId(user_id)})
            current_role = user_data['questionnaire']['career_runway_role_description']
            nodemap_data=nodemap["milestones"]
            journey_list=nodemap_journey(current_role,nodemap_data)
            milestone_details = next((item for item in nodemap_data if item["milestone_id"] == milestone_id), None)
            milestone_data={"milestone_id":milestone_details["milestone_id"],"title":milestone_details["title"],"category":milestone_details["category"]}
            milestone_data_with_timeline={"milestone_id":milestone_details["milestone_id"],"title":milestone_details["title"],"category":milestone_details["category"],"timeline":milestone_details["timeline"]}
            cost_data = Cost_Details.find_one({'nodemap_id': id})   
            
            # if "reason" in data:
            #     reason=data.pop("reason")  
            #     print(reason) 
                

            reason_data = Reason.find_one({'nodemap_id': id})
            update_timeline=data["update_timeline"]
            generate_action=data["generate_actions"]      
            if generate_action == "no":
                
                if "title" in  data:
                    new_title = data["title"]
                    milestone_details["title"] = new_title
                if "start_date" in data:
                    milestone_details["start_date"] = convert_date(data["start_date"])
                    milestone_details["end_date"] =convert_date(data["end_date"])
                    days=days_between( milestone_details["start_date"],milestone_details["end_date"] )
                    milestone_details["timeline"]=f"{days} days"
                if "reason" in data:
                    reason=data["reason"]
                    if reason_data:
                        reason_value={"mile_id":milestone_id,
                                "reason":reason,
                                "created_on":datetime.now()
                            }
                        reason_data["save_reason"]["edit_milestone"].append(reason_value)
                        Reason.update_one({'nodemap_id': id}, {'$set': reason_data})
                    else:
                        reason_value={
                        "user_id":user_id,
                        "nodemap_id": id,
                        "save_reason": {
                        "edit_milestone": [{
                            "mile_id": milestone_id,
                            "reason":reason,
                            "created_on":datetime.now()

                            }],
                            "add_milestone":[],
                            "edit_intermediate":[],
                            "add_intermediate":[],
                            "edit_north_star":[]}}
                        Reason.insert_one(reason_value).inserted_id
                    
                if update_timeline=="yes":
                    index=get_index(nodemap_data,milestone_id)
                    index_data=index+1
                    mile_data=update_milestone_timeline(nodemap["milestones"],index_data)
                    nodemap["milestones"]=mile_data
                          
                dashboard_data.update_one({'_id': ObjectId(id)}, {'$set': nodemap})

                return Response({"message": "Successfully Updated"},status=status.HTTP_200_OK)
            else:
                            reason=data["reason"]
                            new_title=data["title"]     
                            if "start_date" in data:
                                start_date=data["start_date"]
                                milestone_details["start_date"]=convert_date(start_date)
                                end_date=data["end_date"]
                                milestone_details["end_date"]=convert_date(end_date)
                                day=days_between(milestone_details["start_date"],milestone_details["end_date"])
                                timeline=f"{day} days"
                                milestone_details["timeline"]=timeline
                                domain = request.META['HTTP_HOST']
                                if domain=="127.0.0.1:8000":    
                                    path_1 = './Milestones Bucket_2.xlsx'
                                    path_2 = './Milestones Bucket_3.xlsx'
                                else:    
                                    path_1 = '/var/www/html/Backend/Milestones Bucket_2.xlsx'
                                    path_2 = '/var/www/html/Backend/Milestones Bucket_3.xlsx'
                                result,cost=Add_Actions_For_milestones_gpt(journey_list,new_title,milestone_data,timeline,path_1,path_2)
                                numeric_value = float(cost.split('$')[1]) 
                                cost_details=cost_data["variable_costs"]["edit_milestone"]["edit_milestone_cost"][-1]
                                # print(cost_details)
                                
                                cost_details["generate_action_cost"]=cost
                                cost_details["updated_on"]=datetime.now()
                                total_cost=cost_data["variable_costs"]["edit_milestone"]["total_cost"]          
                                value=float(total_cost.split('$')[1])+numeric_value
                                cost_data["variable_costs"]["edit_milestone"]["total_cost"]=f"${str(value)}"
                                fixed_cost=cost_data["fixed_variable_sum"]
                                fixed_value=float(fixed_cost.split('$')[1])+numeric_value
                                cost_data["fixed_variable_sum"]=f"${str(fixed_value)}"
                                Cost_Details.update_one({'nodemap_id': id}, {'$set': cost_data})
                                # print(result)
                                milestone_details["title"]=new_title
                                milestone_details["milestone_description"]=result["milestone_description"]
                                milestone_details["updated_on"] = datetime.now() 
                                milestone_details["actions"]=result["actions"]
                                milestone_details["enablers"]=result["enablers"]
                                act_id = 1 
                                action_start_date=milestone_details["start_date"]
                                for act in milestone_details['actions']:
                                    act["action_id"]=act_id
                                    act['start_date'] = action_start_date
                                    duration = act['duration']
                                    value = str(duration).split(' ')[0]
                                    if str(duration).__contains__('day'):
                                        action_end_date = action_start_date + timedelta(days=int(value))
                                    act['end_date']= action_end_date
                                    act['created_on']= datetime.now()
                                    act['updated_on']= datetime.now()
                                    act['status'] = 0
                                    act_id += 1
                                    action_start_date = action_end_date + timedelta(days=1)
                                enabler_id = 1
                                enabler_list = []
                                for enabler in milestone_details['enablers']:
                                    enabler["enabler_id"]=enabler_id
                                    enabler["progress"]=0
                                    enabler_id += 1
                            else:
                                domain = request.META['HTTP_HOST']
                                if domain=="127.0.0.1:8000":    
                                    path_1 = './Milestones Bucket_2.xlsx'
                                    path_2 = './Milestones Bucket_3.xlsx'
                                else:    
                                    path_1 = '/var/www/html/Backend/Milestones Bucket_2.xlsx'
                                    path_2 = '/var/www/html/Backend/Milestones Bucket_3.xlsx'
                                result,cost=Add_Actions_For_milestones_gpt1(journey_list,new_title,milestone_data_with_timeline,path_1,path_2)
                                numeric_value = float(cost.split('$')[1]) 
                                cost_details=cost_data["variable_costs"]["edit_milestone"]["edit_milestone_cost"][-1]
                                # print(cost_details)
                                
                                cost_details["generate_action_cost"]=cost
                                total_cost=cost_data["variable_costs"]["edit_milestone"]["total_cost"]          
                                value=float(total_cost.split('$')[1])+numeric_value
                                cost_data["variable_costs"]["edit_milestone"]["total_cost"]=f"${str(value)}"
                                fixed_cost=cost_data["fixed_variable_sum"]
                                fixed_value=float(fixed_cost.split('$')[1])+numeric_value
                                cost_data["fixed_variable_sum"]=f"${str(fixed_value)}"
                                Cost_Details.update_one({'nodemap_id': id}, {'$set': cost_data})
                                # print(result)
                                milestone_details["title"]=new_title
                                milestone_details["milestone_description"]=result["milestone_description"]
                                milestone_details["updated_on"] = datetime.now()
                                milestone_details["actions"]=result["actions"]
                                milestone_details["enablers"]=result["enablers"]
                                act_id = 1
                                action_start_date=milestone_details["start_date"]
                                for act in milestone_details['actions']:
                                    act["action_id"]=act_id
                                    act['start_date'] = action_start_date
                                    duration = act['duration']
                                    value = str(duration).split(' ')[0]
                                    if str(duration).__contains__('day'):
                                        action_end_date = action_start_date + timedelta(days=int(value))
                                    act['end_date']= action_end_date
                                    act['created_on']= datetime.now()
                                    act['updated_on']= datetime.now()
                                    act['status'] = 0
                                    act_id += 1
                                    action_start_date = action_end_date + timedelta(days=1)
                                enabler_id = 1
                                enabler_list = []
                                for enabler in milestone_details['enablers']:
                                    enabler["enabler_id"]=enabler_id
                                    enabler["progress"]=0
                                    enabler_id += 1
                            if reason_data:
                                d={"mile_id":milestone_id,
                                     "reason":reason,
                                      "created_on":datetime.now()
                                   }
                                reason_data["save_reason"]["edit_milestone"].append(d)
                                Reason.update_one({'nodemap_id': id}, {'$set': reason_data})
                            else:
                                d={
                                    "user_id":user_id,
                                    "nodemap_id": id,
                                    "save_reason": {
                                   "edit_milestone": [{
                                        "mile_id": milestone_id,
                                        "reason":reason,
                                        "created_on":datetime.now()

                                      }],
                                      "add_milestone":[],
                                      "edit_intermediate":[],
                                      "add_intermediate":[],
                                      "edit_north_star":[]}}
                                Reason.insert_one(d).inserted_id
            
                            if update_timeline=="yes":
                                        index=get_index(nodemap_data,milestone_id)
                                        index_data=index+1
                                        mile_data=update_milestone_timeline(nodemap["milestones"],index_data)
                                        nodemap["milestones"]=mile_data    
            
            dashboard_data.update_one({'_id': ObjectId(id)}, {'$set': nodemap})            
                            

            return Response({"message": "Successfully Updated"},status=status.HTTP_200_OK)           
                            

                    
        
        except json.JSONDecodeError:
            return Response({"message":"Please try again"}, status=status.HTTP_400_BAD_REQUEST)
        except ServiceUnavailableError:
            return Response({"message":"The server is overloaded or not ready yet"}, status=status.HTTP_400_BAD_REQUEST)      
        except RateLimitError: 
            return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



#Add milestone
#validate title

class Add_Milestone_validate_title_View(APIView):
    def post(self, request):
        try:
            request_body = request.body
            data = json.loads(request_body)
            id=data["id"]
            nodemap = dashboard_data.find_one({'_id': ObjectId(id)})
            if not nodemap:
                return Response({"message": "nodemap not found"}, status=status.HTTP_400_BAD_REQUEST)
            
            user_id=nodemap["user_id"]
            user_data = users_registration.find_one({'_id': ObjectId(user_id)})
            current_role = user_data['questionnaire']['career_runway_role_description']
            nodemap_data=nodemap["milestones"]
            journey_list=nodemap_journey(current_role,nodemap_data)
            # selected_runway=user_data["questionnaire"]["selected_user_journey"]
            reason = data["reason"]
            new_title = data["title"]  
            milestone=nodemap["milestones"] 
            # limit=len(milestone)
            # # l=8-limit
            # # if limit>5:
            # #     return Response({"message": "Add action limit is more "})
            # if limit>=8:
            #     return Response({"message": "You have already 8 milestones you can't add "},status=status.HTTP_400_BAD_REQUEST)
                             
          
            result,cost= Add_milestones_validate_title_gpt(journey_list,new_title)
            cost_data = Cost_Details.find_one({'nodemap_id': id})
            # print(cost_data)
            # print(cost)
            numeric_value = float(cost.split('$')[1])
            validate_milestone_cost={"mile_id":"",
                                     "validate_title_cost":cost,
                                     "generate_milestone_cost":"",
                                     "created_on":datetime.now()}
            
            cost_data["variable_costs"]["add_milestone"]["add_milestone_cost"].append(validate_milestone_cost)
            total_cost=cost_data["variable_costs"]["add_milestone"]         
            if total_cost["total_cost"] =="0":
                total_cost["total_cost"]=cost
                total_cost["updated_on"]=datetime.now()

            else:
                total_cost_data=cost_data["variable_costs"]["add_milestone"]["total_cost"]
                value=float(total_cost_data.split('$')[1])+numeric_value
                total_cost["total_cost"] =f"${str(value)}"
                total_cost["updated_on"]=datetime.now()
            if cost_data["fixed_variable_sum"]=="0":
                cost_data["fixed_variable_sum"]=cost
            else:
                fixed_cost=cost_data["fixed_variable_sum"]
                value=float(fixed_cost.split('$')[1])+numeric_value
                cost_data["fixed_variable_sum"]=f"${str(value)}"
            Cost_Details.update_one({'nodemap_id': id}, {'$set': cost_data})
            
            if result=="yes":
                return Response({"matching": result},status=status.HTTP_200_OK)   
            return Response({"matching": result},status=status.HTTP_200_OK)
        except json.JSONDecodeError:
            return Response({"message":"Please try again"}, status=status.HTTP_400_BAD_REQUEST)
        except ServiceUnavailableError:
            return Response({"message":"The server is overloaded or not ready yet"}, status=status.HTTP_400_BAD_REQUEST)      
        except RateLimitError: 
            return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




#Add milestone path specify
class Add_Milestone_Path_view(APIView):
    def get(self, request,id):
        try:        
            nodemap = dashboard_data.find_one({'_id': ObjectId(id)})
            if not nodemap:
                return Response({"message": "nodemap not found"}, status=status.HTTP_400_BAD_REQUEST)
        
            milestones=nodemap["milestones"]
            path=[]
            for milestone in milestones:
                if milestone["progress"]==0 and milestone["type"] !="targeted_role":
                    milestone_id=milestone["milestone_id"]
                    milestone_title=milestone["title"]
                    data={"milestone_id":milestone_id,"milestone_title":milestone_title}
                    path.append(data)
              
            return Response({"response": path},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#Add milestone details update

#update milestone
class Add_Milestone_View(APIView):
    def post(self, request):
        try:
            request_body = request.body
            data = json.loads(request_body)
            id=data["id"]
            nodemap = dashboard_data.find_one({'_id': ObjectId(id)})

            if not nodemap:
                return Response({"message": "nodemap not found"}, status=status.HTTP_400_BAD_REQUEST)
                
            user_id=nodemap["user_id"]
            
            user_data = users_registration.find_one({'_id': ObjectId(user_id)})
            # current_role = user_data['questionnaire']['career_runway_role_description']
            nodemap_data=nodemap["milestones"]
            cost_data = Cost_Details.find_one({'nodemap_id': id})
            # journey_list=nodemap_journey(current_role,nodemap_data)
            # selected_runway=user_data["questionnaire"]["selected_user_journey"]
            # del nodemap['_id']
            # del nodemap["user_id"]
            reason = data["reason"]
            reason_data = Reason.find_one({'nodemap_id': id})
            update_timeline=data["update_timeline"]
            generate_action_and_enablers=data["generate_actions_and_enablers"]        
            if generate_action_and_enablers == "no":
                new_title=data["title"]
                domain = request.META['HTTP_HOST']
                if domain=="127.0.0.1:8000":    
                    path_1 = './Milestones Bucket_2.xlsx'
                    path_2 = './Milestones Bucket_3.xlsx'
                else:    
                    path_1 = '/var/www/html/Backend/Milestones Bucket_2.xlsx'
                    path_2 = '/var/www/html/Backend/Milestones Bucket_3.xlsx'

                result,cost=Add_milestones_gpt(new_title,path_1,path_2)
                milestone_description=result["milestone_description"]
                type=result["type"]
                category=result["category"]
                start_date=data["start_date"]
                start_date=convert_date(start_date)
                end_date=data["end_date"]
                end_date=convert_date(end_date)
                timeline=days_between(start_date,end_date)
                # print(timeline)
                milestone_data={
                    "milestone_id":str(uuid.uuid4()),
                    "title":new_title,
                    "milestone_description":milestone_description,
                    "timeline":f"{timeline} days ",
                    "type":type.lower(),
                    "category":category,
                    "progress":0,
                    "start_date":start_date,
                    "end_date":end_date,
                    "actions":[],
                    "created_on":datetime.now(),
                    "updated_on":datetime.now()



                }
                # print(milestone_data)
                id_data=data["milestone_id"]
                milestone=nodemap["milestones"]
                # print(milestone)
                index=get_index(milestone,id_data)
                milestone.insert(index + 1,milestone_data)
                #save reason
                if reason_data:
                    d={
                    "mile_id":milestone_data["milestone_id"],
                   "reason":reason,
                    "created_on":datetime.now()
                   }
                    reason_data["save_reason"]["add_milestone"].append(d)
                    Reason.update_one({'nodemap_id': id}, {'$set': reason_data})
                else:
                    d={
                        "user_id":user_id,
                        "nodemap_id": id,
                        "save_reason": {
                    "edit_milestone": [],
                        "add_milestone":[{
                            "mile_id":milestone_data["milestone_id"],
                            "reason":reason,
                            "created_on":datetime.now()

                        }],
                        "edit_intermediate":[],
                        "add_intermediate":[],
                        "edit_north_star":[]}}
                    Reason.insert_one(d).inserted_id
                numeric_value = float(cost.split('$')[1])
                cost_details=cost_data["variable_costs"]["add_milestone"]["add_milestone_cost"][-1]
                # print(cost_details)
                cost_details["mile_id"]=milestone_data["milestone_id"]
                cost_details["generate_milestone_cost"]=cost
                cost_details["updated_on"]=datetime.now()
                total_cost=cost_data["variable_costs"]["add_milestone"]          
                total_cost_data=cost_data["variable_costs"]["add_milestone"]["total_cost"]
                value=float(total_cost_data.split('$')[1])+numeric_value
                total_cost["total_cost"]=f"${str(value)}"
                total_cost["updated_on"]=datetime.now()
                fixed_cost=cost_data["fixed_variable_sum"]
                value=float(fixed_cost.split('$')[1])+numeric_value
                cost_data["fixed_variable_sum"]=f"${str(value)}"
                cost_data["updated_on"]=datetime.now()
                Cost_Details.update_one({'nodemap_id': id}, {'$set': cost_data})
                #North star progress
                northstar_progress=north_star_progress(nodemap["milestones"])
                mile_details=nodemap["milestones"][-1]
                mile_progress=milestone_progress(mile_details["actions"],mile_details["enablers"])
                n_progress=(100/len(nodemap["milestones"]))*(mile_progress/100)
                if  isinstance(n_progress,float):
                    nstar_progress=round(n_progress, 2)
                if isinstance(n_progress,int):
                    nstar_progress=n_progress
                mile_details["progress"]=northstar_progress+nstar_progress
                mile_details["updated_on"]=datetime.now()


                if update_timeline=="yes":
                    milestone_details=nodemap["milestones"]
                    index_data=index+2
                    mile_data=update_milestone_timeline(milestone_details,index_data)
                    nodemap["milestones"]=mile_data
                
            
                dashboard_data.update_one({'_id': ObjectId(id)}, {'$set': nodemap})
                return Response({"message": "Successfully Created"},status=status.HTTP_200_OK)
            else:
                new_title = data["title"] 
               
                start_date=data["start_date"]
                start_date=convert_date(start_date)
                end_date=data["end_date"]
                end_date=convert_date(end_date)
                timeline=days_between(start_date,end_date)
                months=f"{timeline} days"
                domain = request.META['HTTP_HOST']
                if domain=="127.0.0.1:8000":    
                    path_1 = './Milestones Bucket_2.xlsx'
                    path_2 = './Milestones Bucket_3.xlsx'
                else:    
                    path_1 = '/var/www/html/Backend/Milestones Bucket_2.xlsx'
                    path_2 = '/var/www/html/Backend/Milestones Bucket_3.xlsx'
                result,cost=Add_actions_ce_for_milestone_gpt(new_title,months,path_1,path_2)
                # print(result)
                result["type"]=result["type"].lower()
                result["timeline"]=months
                # print(result)
                result['milestone_id'] = str(uuid.uuid4())
                result['progress'] = 0
                result['start_date']= start_date
                action_start_date = start_date
                duration = result['timeline']
                value = str(duration).split(' ')[0]
                if str(duration).__contains__('day'):
                    end_date = start_date + timedelta(days=int(value))
                                        
                result['end_date']= end_date
                result['created_on']= datetime.now()
                result['updated_on']= datetime.now()
                start_date = end_date + timedelta(days=1)
                act_id = 1
                for act in result['actions']:
                        act['action_id'] = act_id
                        act['start_date'] = action_start_date
                        duration = act['duration']
                        value = str(duration).split(' ')[0]
                        if str(duration).__contains__('day'):
                           
                            action_end_date = action_start_date + timedelta(days=int(value))
                        act['end_date']= action_end_date
                        act['created_on']= datetime.now()
                        act['updated_on']= datetime.now()
                        act['status'] = 0
                        act_id += 1
                        action_start_date = action_end_date + timedelta(days=1)
                enabler_id = 1
                enabler_list = []
                for enabler in result['enablers']:
                    enabler["enabler_id"]=enabler_id
                    enabler["progress"]=0
                    enabler_id += 1
                # print(result)
                id_data=data["milestone_id"]
                milestone=nodemap["milestones"]
                # print(milestone)
                index=get_index(milestone,id_data)
                milestone.insert(index + 1,result)
                 #save reason
                if reason_data:
                    d={
                    "mile_id":result["milestone_id"],
                   "reason":reason,
                    "created_on":datetime.now()
                   }
                    reason_data["save_reason"]["add_milestone"].append(d)
                    Reason.update_one({'nodemap_id': id}, {'$set': reason_data})
                else:
                    d={
                        "user_id":user_id,
                        "nodemap_id": id,
                        "save_reason": {
                    "edit_milestone": [],
                        "add_milestone":[{
                            "mile_id":result["milestone_id"],
                            "reason":reason,
                            "created_on":datetime.now()

                        }],
                        "edit_intermediate":[],
                        "add_intermediate":[],
                        "edit_north_star":[]}}
                    Reason.insert_one(d).inserted_id
                numeric_value = float(cost.split('$')[1])
                cost_details=cost_data["variable_costs"]["add_milestone"]["add_milestone_cost"][-1]
                # print(cost_details)
                cost_details["mile_id"]=result["milestone_id"]
                cost_details["generate_milestone_cost"]=cost
                cost_details["updated_on"]=datetime.now()
                total_cost=cost_data["variable_costs"]["add_milestone"]
                total_cost_data=cost_data["variable_costs"]["add_milestone"]["total_cost"]
                value=float(total_cost_data.split('$')[1])+numeric_value
                total_cost["total_cost"]=f"${str(value)}"
                total_cost["updated_on"]=datetime.now()
                fixed_cost=cost_data["fixed_variable_sum"]
                value=float(fixed_cost.split('$')[1])+numeric_value
                cost_data["fixed_variable_sum"]=f"${str(value)}"
                cost_data["updated_on"]=datetime.now()
                Cost_Details.update_one({'nodemap_id': id}, {'$set': cost_data})
                #calculate north star progress
                northstar_progress=north_star_progress(nodemap["milestones"])
                mile_details=nodemap["milestones"][-1]
                mile_progress=milestone_progress(mile_details["actions"],mile_details["enablers"])
                n_progress=(100/len(nodemap["milestones"]))*(mile_progress/100)
                if  isinstance(n_progress,float):
                    nstar_progress=round(n_progress, 2)
                if isinstance(n_progress,int):
                    nstar_progress=n_progress
                mile_details["progress"]=northstar_progress+nstar_progress
                mile_details["updated_on"]=datetime.now()
                if update_timeline=="yes":
                    milestone_details=nodemap["milestones"]
                    index_data=index+2
                    mile_data=update_milestone_timeline(milestone_details,index_data)
                    nodemap["milestones"]=mile_data
            
                dashboard_data.update_one({'_id': ObjectId(id)}, {'$set': nodemap})            
                            

                return Response({"message": "Successfully Created"},status=status.HTTP_200_OK)
        except json.JSONDecodeError:
            return Response({"message":"Please try again"}, status=status.HTTP_400_BAD_REQUEST)
        except ServiceUnavailableError:
            return Response({"message":"The server is overloaded or not ready yet"}, status=status.HTTP_400_BAD_REQUEST)      
        except RateLimitError: 
            return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

'''Edit North Star'''
class EditNorthStar(APIView):
    def patch(self,request,id):
        try:
            request_data=request.body
            data=json.loads(request_data)
            milestone_id=data.pop('milestone_id')
            if 'reason' in data:
                reason=data.pop('reason')
            else:
                reason = None
            generate_milestone=data.pop('generate_milestone')
            dashboard_obj = dashboard_data.find_one({"_id": ObjectId(id)})
            if not dashboard_obj:
                return Response({"message": "No data found"}, status=status.HTTP_400_BAD_REQUEST)
            
            mile_obj = dashboard_data.find_one({ "milestones": { '$elemMatch': { "milestone_id": milestone_id } }})
            if not mile_obj:
                return Response({"message": "Invalid Milestone ID"}, status=status.HTTP_400_BAD_REQUEST)
            
            user_id = dashboard_obj['user_id']
            get_user_data = users_registration.find_one({'_id':ObjectId(user_id)})
            if not get_user_data:
                return Response({"message": "No questionnaire data found"}, status=status.HTTP_400_BAD_REQUEST)
            current_role = get_user_data['questionnaire']['career_runway_role_description']['role']
            ns_progress_timeline = get_user_data['questionnaire']['career_runway_duration']
            ns_progress_timeline = int(ns_progress_timeline * 30)
            
            milestones = dashboard_obj.get("milestones",[])
            milestone_duration_days = sum(int(str(milestone['timeline']).split(' ')[0]) for milestone in milestones)
            target_data = milestones[len(milestones)-1]
            
            old_target_title = target_data['title']
            if target_data:
                if 'role_details' in data:
                    role_details=data.pop('role_details')
                    target_data['targeted_role'].update(role_details)
                if "start_date" in data:
                    start_date_str = data['start_date']
                    converted_date = convert_date(start_date_str)
                    # print(converted_date)
                    data['start_date'] = converted_date
                if "end_date" in data:
                    end_date_str = data['end_date']
                    converted_date = convert_date(end_date_str)
                    # print(converted_date)
                    data['end_date'] = converted_date
                    date_diff = date_difference(start_date_str,end_date_str)
                    data['timeline'] = f"{date_diff} day(s)"
                target_data.update(data)
                
                target_data["updated_on"]=datetime.now()
            dashboard_data.update_one({'_id':ObjectId(id)},{'$set': dashboard_obj})

            if str(generate_milestone).lower() == "yes":
                new_target_title = target_data['title']
                new_target_rank = target_data['targeted_role']['rank']
                # print(new_target_title)
                target_list = target_data['targeted_role']
                title_list = []
                timeline_sum = 0
                for idx,mile in enumerate(milestones):
                    actions_list = []
                    for actions in mile['actions']:
                        if actions['status'] != 0:
                            actions_list.append(actions['title'])
                            duration = actions['duration']
                            value = str(duration).split(' ')[0]
                            timeline_sum += int(value) 
                    if actions_list:
                            completed_milestones = {'milestone_title': mile['title'],'actions': actions_list}
                            title_list.append(completed_milestones)
                            last_end_date = mile['end_date']
                            current_date = datetime.now()
                            if last_end_date < current_date - timedelta(days=1):
                                last_end_date = current_date
                            edit_ns_index = idx            
                timeline = milestone_duration_days - timeline_sum
                domain = request.META['HTTP_HOST']
                if domain=="127.0.0.1:8000":    
                    path_1 = './Milestones Bucket_2.xlsx'
                    path_2 = './Milestones Bucket_3.xlsx'
                else:    
                    path_1 = '/var/www/html/Backend/Milestones Bucket_2.xlsx'
                    path_2 = '/var/www/html/Backend/Milestones Bucket_3.xlsx'
                if title_list:
                    if edit_ns_index + 1 == len(milestones):
                        target_list = target_data['targeted_role']
                        target_rank = target_data['targeted_role']['rank']
                        new_milestones, cost = north_star_progress_milestone(current_role,old_target_title,target_rank,new_target_title,title_list,ns_progress_timeline,path_1,path_2)
                        last_end_date = datetime.now()
                        restructured_target = north_star_progress_restructure(new_milestones['milestones'],last_end_date,target_list)
                        milestones = milestones[:edit_ns_index] + list (restructured_target)
                        dashboard_obj['milestones'] = milestones
                    else:
                        new_milestones, cost = north_star_milestone(current_role,old_target_title,new_target_rank,new_target_title,title_list,timeline,path_1,path_2)
                        restructured_target = new_target_nodemap(new_milestones['milestones'],last_end_date, target_list)
                        milestones = milestones[:edit_ns_index + 1] + list (restructured_target)
                        dashboard_obj['milestones'] = milestones
                else:
                    last_end_date = datetime.now()
                    new_milestones, cost = north_star_milestone(current_role,old_target_title,new_target_rank,new_target_title,title_list,timeline,path_1,path_2)
                    # print(new_milestones)
                    restructured_target = new_target_nodemap(new_milestones['milestones'],last_end_date, target_list)
                    dashboard_obj['milestones'] = restructured_target
                    
                ns_progress=north_star_progress(dashboard_obj["milestones"])
                mile_data=dashboard_obj["milestones"][-1]
                mile_data['progress'] = ns_progress
                dashboard_data.replace_one({"_id": ObjectId(id)}, dashboard_obj)
                cost_data = Cost_Details.find_one({'nodemap_id': id})
                numeric_value = float(cost.split('$')[1])
                validate_milestone_cost={"mile_id":milestone_id,
                                        "generate_milestone_cost":cost,
                                        "created_on":datetime.now()}
                
                cost_data["variable_costs"]["edit_northstar"]["edit_northstar_cost"].append(validate_milestone_cost)
                total_cost=cost_data["variable_costs"]["edit_northstar"]  
            
                if total_cost["total_cost"] =="0":
                    total_cost["total_cost"]=cost
                    total_cost["updated_on"]=datetime.now()
                else:
                    total_cost_data=cost_data["variable_costs"]["edit_northstar"]["total_cost"]
                    value=float(total_cost_data.split('$')[1])+numeric_value
                    total_cost["total_cost"] =f"${str(value)}"
                    total_cost["updated_on"]=datetime.now()
                if cost_data["fixed_variable_sum"]=="0":
                    cost_data["fixed_variable_sum"]=cost
                else:
                    fixed_cost=cost_data["fixed_variable_sum"]
                    value=float(fixed_cost.split('$')[1])+numeric_value
                    cost_data["fixed_variable_sum"]=f"${str(value)}"

                Cost_Details.update_one({'nodemap_id': id}, {'$set': cost_data})
            if reason != None:
                reason_data = Reason.find_one({'nodemap_id': id})
                if reason_data:
                    d={"mile_id":milestone_id,
                    "reason":reason,
                        "created_on":datetime.now()
                    }
                    reason_data["save_reason"]["edit_north_star"].append(d)
                    Reason.update_one({'nodemap_id': id}, {'$set': reason_data})
                else:
                    d={
                        "user_id":user_id,
                        "nodemap_id": id,
                        "save_reason": {
                        "edit_north_star": [{
                            "mile_id": milestone_id,
                            "reason":reason,
                            "created_on":datetime.now()

                        }],
                        "add_milestone":[],
                        "edit_intermediate":[],
                        "add_intermediate":[],
                        "edit_milestone":[]}}
                    Reason.insert_one(d).inserted_id
            return Response({"message":"successfully updated"},status=status.HTTP_200_OK)
        except json.JSONDecodeError:
            return Response({"message":"Please try again"}, status=status.HTTP_400_BAD_REQUEST)
        except ServiceUnavailableError:
            return Response({"message":"The server is overloaded or not ready yet"}, status=status.HTTP_400_BAD_REQUEST)      
        except RateLimitError: 
            return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)       
        except Exception as e:
            return Response({"message": "An error occured","error" :str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)       
        
        

#update milestone/intermediate role/north star progress

class Milestone_Progress__View(APIView):
    def patch(self, request,id):
        try:
            request_body = request.body
            data = json.loads(request_body)
        
            milestone_id=data["milestone_id"]
            nodemap = dashboard_data.find_one({'_id': ObjectId(id)})

            if not nodemap:
                return Response({"message": "nodemap not found"}, status=status.HTTP_400_BAD_REQUEST)
            mile_obj = dashboard_data.find_one({ "milestones": { '$elemMatch': { "milestone_id": milestone_id } }})
            if not mile_obj:
                return Response({"message": "Invalid Milestone ID"}, status=status.HTTP_400_BAD_REQUEST)
            nodemap_data=nodemap["milestones"]
     
            milestone_details = next((item for item in nodemap_data if item["milestone_id"] == milestone_id), None)
            mile_progress=data["progress"]
            mile_type=milestone_details["type"]
            if mile_type=="targeted_role":
                if mile_progress==100:
                    for mile in nodemap_data:
                        if "actions" in mile:
                            actions=mile["actions"]
                            for i in actions:
                                i["status"]=2
                        if "enablers" in mile:
                            enablers=mile["enablers"]
                            for j in enablers:
                               j["progress"]=100
                        mile["progress"]=100
                        mile["updated_on"]=datetime.now()
                else:
                    milestone_details["progress"]=mile_progress
                    milestone_details["updated_on"]=datetime.now() 
            else:
                if mile_progress==100:
                    if "actions" in milestone_details :
                       for i in milestone_details["actions"]:
                           i["status"]=2
                    if "enablers" in milestone_details:
                        for j in milestone_details["enablers"]:
                            j["progress"]=100
                    milestone_details["progress"]=mile_progress
                    milestone_details["updated_on"]=datetime.now()
                
                else:     
                    milestone_details["progress"]=mile_progress
                    milestone_details["updated_on"]=datetime.now()
                northstar_progress=north_star_progress(nodemap["milestones"])
                mile_data=nodemap["milestones"][-1]
                mile_progress=milestone_progress(mile_data["actions"],mile_data["enablers"])
                n_progress=(100/len(nodemap["milestones"]))*(mile_progress/100)
                if  isinstance(n_progress,float):
                    nstar_progress=round(n_progress, 2)
                if isinstance(n_progress,int):
                    nstar_progress=n_progress
                mile_data["progress"]=northstar_progress+nstar_progress
                mile_data["updated_on"]=datetime.now()    
               
                    
            dashboard_data.update_one({'_id': ObjectId(id)}, {'$set': nodemap})
            return Response({"message":"sucessfully updated"},status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        

class Critical_Enablers(APIView):
    def get(self, request):
        query = request.GET.get('q', '')

        try:
            # Fetch all names from the critical_enablers array
            all_names = critical_enablers.distinct("critical_enablers.name")

            # Filter names using
            starts_with_query = [name for name in all_names if name.lower().startswith(query.lower())]
            contains_query = [name for name in all_names if query.lower() in name.lower() and name not in starts_with_query]

            # Combine the lists in the desired order
            matching_names = starts_with_query + contains_query 

            if matching_names:
                return Response({"result": matching_names}, status=status.HTTP_200_OK)
            else:
                return Response({"message": f"No matching critical enablers found for '{query}'"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"message": "An error occurred", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
