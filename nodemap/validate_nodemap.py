from langchain.chains import LLMChain
from langchain.callbacks import get_openai_callback
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import json
import uuid

'''converts date obj in nodemap to str for nodemap API'''
def nodemap_date_to_string(nodemap_structure):
    for mile in nodemap_structure:
        mile['start_date'] = datetime.date(mile['start_date']).strftime('%d/%m/%Y')
        mile['end_date'] = datetime.date(mile['end_date']).strftime('%d/%m/%Y')
        for act in mile['actions']:
            act['start_date'] = datetime.date(act['start_date']).strftime('%d/%m/%Y')
            act['end_date'] = datetime.date(act['end_date']).strftime('%d/%m/%Y')  
    return nodemap_structure

'''converts date in str to date obj'''
def convert_date(date=None):
    if date is not None:
        formatted_date = datetime.strptime(date, '%d/%m/%Y')
        return formatted_date
    
'''calculates date difference between start and end date'''
def date_difference(start_date_str,end_date_str):
    start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
    end_date = datetime.strptime(end_date_str, '%d/%m/%Y')
    date_diff = end_date - start_date
    return date_diff.days
def days_between(start_date, end_date):
    
    # Calculate the total number of days
    delta = end_date - start_date
    total_days = delta.days
    return total_days
def get_index(milestone,id):
    index = None  # Initialize index to None (not found) by default

    for i, item in enumerate(milestone):
    #   print(item)
      if item["milestone_id"] == id:
        index = i
        break

    if index is not None:
        return index

def milestone_progress(actions,enablers):
    sum=0
    count=0
    for i in actions:
        if i["status"]==2:
            sum=sum+100
        count=count+1
    for j in enablers:
        sum=sum+j["progress"]
        count=count+1
    mile_progress=sum/count
    if isinstance(mile_progress, int):
        return mile_progress
    if isinstance(mile_progress,float):
       return round(mile_progress, 2)
    
#North star progress
def north_star_progress(milestones):
     sum=0
     for k in milestones:
         if k["progress"]==100:
             sum=sum+k["progress"]
     avg=sum/len(milestones)
     if isinstance(avg, int):
        return avg
          
     if isinstance(avg,float):
         return round(avg, 2)
       

  
#update milestone timeline

def update_milestone_timeline(milestone_details,index_data):
    if index_data < len(milestone_details):
        for index in range(index_data, len(milestone_details)):
            mile_data = milestone_details[index]
            previous_index_data=milestone_details[index-1]
            previous_index_data_end_date=previous_index_data["end_date"] + timedelta(days=1)
            mile_data["start_date"]=previous_index_data_end_date
            time_line=mile_data["timeline"]
            value = str(time_line).split(' ')[0]
            
            if str(time_line).__contains__('day'):
                new_end_date = mile_data["start_date"] + timedelta(days=int(value))
            mile_data["end_date"]=new_end_date
            mile_data["updated_on"]=datetime.now()
        return milestone_details

'''Edit intermediate title validate prompt'''
def intermediate_validate(milestone_id,new_journey_structure,old_title,new_title):
    current_role = new_journey_structure['current_role']
    targeted_role = new_journey_structure['targeted_role']['title']
    intermediate_roles = new_journey_structure['intermediate_roles']
   
    query = f"I am currently in a role :'{current_role}' and I want to become a {targeted_role}. To achieve my targeted_role I have chosen a specific career path : {new_journey_structure}. Please evaluate the details and as a career guidance expert tell me when I change the '{old_title}' career stream mentioned in {intermediate_roles}{milestone_id} to this '{new_title}' career stream whether it will align with this chosen specific career path{new_journey_structure} .Respond with 'yes' if the {new_title} is relevant to the career path, and 'no' if it's not with out any explanation."

    llm = ChatOpenAI(model="gpt-4",temperature=0.18)
    prompt = PromptTemplate(
    input_variables=["job_recommend"],
    template = "{job_recommend}"
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    with get_openai_callback() as cb:
        response = chain.run({
                            "job_recommend":query
                            })
    tokens = {
            "Total Tokens": cb.total_tokens,
            "Prompt Tokens": cb.prompt_tokens,
            "Completion Tokens": cb.completion_tokens,
            "Total Cost (USD)": f"${cb.total_cost}"
        }
    print(tokens)
    return response, tokens['Total Cost (USD)']

'''Add intermediate title validate prompt'''
def validate_addintermediate_title(new_journey_structure,new_title):
    current_role = new_journey_structure['current_role']
    targeted_role = new_journey_structure['targeted_role']['title']
    intermediate_roles = new_journey_structure['intermediate_roles']
   
    query = f"I am currently in a role :'{current_role}' and I want to become a {targeted_role}. To achieve my targeted_role I have chosen a specific career path : {new_journey_structure}. Please evaluate the details and as a career guidance expert tell me whether this role: '{new_title}' will align with this chosen specific career path{new_journey_structure} .Respond with 'yes' if the {new_title} is relevant to the career path, and 'no' if it's not with out any explanation."

    llm = ChatOpenAI(model="gpt-4",temperature=0.18)
    prompt = PromptTemplate(
    input_variables=["job_recommend"],
    template = "{job_recommend}"
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    with get_openai_callback() as cb:
        response = chain.run({
                            "job_recommend":query
                            })
    tokens = {
            "Total Tokens": cb.total_tokens,
            "Prompt Tokens": cb.prompt_tokens,
            "Completion Tokens": cb.completion_tokens,
            "Total Cost (USD)": f"${cb.total_cost}"
        }
    print(tokens)
    return response, tokens['Total Cost (USD)']

'''Edit intermediate prompt'''
def generate_milestone_actions(journey_list,current_title,new_title_rank,new_title,new_timeline,path_1): 
    response_1 = pd.read_excel(path_1).to_json(orient="records")
    milestone_1 = json.loads(response_1)
    
    if not journey_list:

        query = f"""My current_role is {current_title} and I want to become a {new_title_rank}{new_title}.
            Note :For the transition from {current_title} to {new_title_rank}{new_title} suggest me some minimum of 2 milestones(maximum 3) necessary to achieve the role of {new_title_rank} {new_title}(# root key ‘milestones’)  
            For each milestone, provide the following details:
            1. Title (key: 'title'): Ensure the milestone 'title' to be very specific related to the actions and not the role name(#max 100 characters).
            2. Milestone Description (key: 'milestone_description'): Describe the milestone.
            3. Milestone Type (key: 'type' value:'milestone').
            4. Actions (key: 'actions'): Suggest up to maximum 5 actions to achieve the milestone.
            5.From {milestone_1} analyse milestone['milestone_category'] and milestone['actions_to_track_and_complete'] details into consideration while generating the milestones and actions for a milestone(Please do not return these  milestone['milestone_category'] and milestone['actions_to_track_and_complete'] value in milestone 'title' and action 'title' response). But specify the milestone category(Key:'category') to which each milestones belong to.
            6.I want you to Divide the total timeline(key:‘timeline’ format: X day(s) #include this key for each milestone,this should sum up the action duration) of {new_timeline} day(s) suitably across each milestones.For each milestone, allocate a duration for each action (key: 'duration' (format:X day(s) by dividing the ‘duration’ within the milestone ‘timeline’)). Also,provide the ’title’ (# specifying any online courses, platforms, projects, or institutes along with the title(#max 150 characters) that can help achieve the action)and ‘description’ for each action.
            Additionally, suggest up to three critical enablers (key: 'enablers') for each milestone, chosen from the following list: [Growth mindset, Self-discipline, Optimism, Proactivity, Reflective thinking, Self-awareness, Attitude, Strategic thinking, Goal-setting, Creativity, Analytical thinking, Financial literacy, Learning agility, Leadership, Adaptability, Flexibility, Cultural competence, Conflict resolution, Active listening, Decision-making, Relationship building, Feedback-seeking].
            Return the response in proper JSON format(# root key ‘milestones’) without any explanations."""
    
    else:
        print("With journey list")
        query = f"""My current_role is {current_title} and I want to become a {new_title_rank}{new_title}. I have completed few milestones mentioned in this journey list: {journey_list} already.
            Note :For the transition from {current_title} to {new_title_rank}{new_title} make sure you don't repeat the milestones and actions mentioned in the journey list:{journey_list} but suggest me some new mimimum 2 milestones(maximum 3) necessary to achieve {new_title_rank}{new_title}.(# root key ‘milestones’)  
            For each milestone, provide the following details:
            1. Title (key: 'title'): Ensure the milestone 'title' to be very specific related to the actions and not the role name(#max 100 characters).
            2. Milestone Description (key: 'milestone_description'): Describe the milestone.
            3. Milestone Type (key: 'type' value:'milestone').
            4. Actions (key: 'actions'): Suggest up to maximum 5 actions to achieve the milestone.
            5.From {milestone_1} analyse milestone['milestone_category'] and milestone['actions_to_track_and_complete'] details into consideration while generating the milestones and actions for a milestone(Please do not return these  milestone['milestone_category'] and milestone['actions_to_track_and_complete'] value in milestone 'title' and action 'title' response). But specify the milestone category(Key:'category') to which each milestones belong to.
            6.I want you to Divide the total timeline(key:‘timeline’ format: X day(s) #include this key for each milestone,this should sum up the action duration) of {new_timeline} day(s) suitably across each milestones.For each milestone, allocate a duration for each action (key: 'duration' (format:X day(s) by dividing the ‘duration’ within the milestone ‘timeline’)). Also,provide the ’title’ (# specifying any online courses, platforms, projects, or institutes along with the title(#max 150 characters) that can help achieve the action)and ‘description’ for each action.
            Additionally, suggest up to three critical enablers (key: 'enablers') for each milestone, chosen from the following list: [Growth mindset, Self-discipline, Optimism, Proactivity, Reflective thinking, Self-awareness, Attitude, Strategic thinking, Goal-setting, Creativity, Analytical thinking, Financial literacy, Learning agility, Leadership, Adaptability, Flexibility, Cultural competence, Conflict resolution, Active listening, Decision-making, Relationship building, Feedback-seeking].
            Return the response in proper JSON format(# root key ‘milestones’) without any explanations."""
    
    llm = ChatOpenAI(model="gpt-4",temperature=0.18)
    prompt = PromptTemplate(
    input_variables=["job_recommend"],
    template = "{job_recommend}"
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    with get_openai_callback() as cb:
        response = chain.run({
                            "job_recommend":query
                            })
    tokens = {
            "Total Tokens": cb.total_tokens,
            "Prompt Tokens": cb.prompt_tokens,
            "Completion Tokens": cb.completion_tokens,
            "Total Cost (USD)": f"${cb.total_cost}"
        }
    print(tokens)
    response = json.loads(response)
    return response, tokens['Total Cost (USD)']

'''Edit intermediate restructuring'''
def edit_inter_restructure(new_data,last_mile_date):
    start_date = last_mile_date
    for data in new_data:
        data['milestone_id'] = str(uuid.uuid4())
        data['progress'] = 0 
        data['start_date']= start_date
        action_start_date = start_date
        duration = data['timeline']
        value = str(duration).split(' ')[0]
        if str(duration).__contains__('day'):
            end_date = start_date + timedelta(days=int(value))
        data['end_date']= end_date
        data['created_on']= datetime.now()
        data['updated_on']= datetime.now()
        start_date = end_date + timedelta(days=1)
        action_id = 1
        for actions in data['actions']:
            actions['action_id'] = action_id
            actions['start_date'] = action_start_date
            duration = actions['duration']
            value = str(duration).split(' ')[0]
            if str(duration).__contains__('day'):
                action_end_date = action_start_date + timedelta(days=int(value))
            actions['end_date']= action_end_date
            actions['status'] = 0
            actions['created_on']= datetime.now()
            actions['updated_on']= datetime.now()
            action_id+=1
            action_start_date = action_end_date + timedelta(days=1)
        enabler_list = []
        enabler_id = 1
        for enabler in data['enablers']:
            enabler_list.append(
            {
                "enabler_id": enabler_id,
                "title": enabler,
                "progress": 0
            })
            enabler_id += 1
        data['enablers'] = enabler_list
    return new_data

'''add intermediate restructuring'''
def new_nodemap(new_data,inter_list,target_list,last_mile_date):
    start_date = last_mile_date + timedelta(days=1)
    n=0
    for data in new_data:
        if data['type'] == 'intermediate_role':
            data['intermediate_role'] = inter_list[n]
            n=n+1
        if data['type'] == 'targeted_role':
            data['targeted_role'] = target_list[0]

        data['milestone_id'] = str(uuid.uuid4())
        data['progress'] = 0 
        data['start_date']= start_date
        action_start_date = start_date
        duration = data['timeline']
        value = str(duration).split(' ')[0]
        if str(duration).__contains__('month'):
            if float(value) == 0.5:
                end_date = start_date + timedelta(days=15)
            else:
                end_date = start_date + relativedelta(months=int(value))
        if str(duration).__contains__('week'):
            end_date = start_date + timedelta(weeks=int(value))
        if str(duration).__contains__('day'):
            end_date = start_date + timedelta(days=int(value))
        data['end_date']= end_date
        data['created_on']= datetime.now()
        data['updated_on']= datetime.now()
        start_date = end_date + timedelta(days=1)
        action_id = 1
        for actions in data['actions']:
            actions['action_id'] = action_id
            actions['start_date'] = action_start_date
            duration = actions['duration']
            value = str(duration).split(' ')[0]
            if str(duration).__contains__('month'):
                if float(value) == 0.5:
                    action_end_date = action_start_date + timedelta(days=15)
                else:
                    action_end_date = action_start_date + relativedelta(months=int(value))
            if str(duration).__contains__('week'):
                action_end_date = action_start_date + timedelta(weeks=int(value))
            if str(duration).__contains__('day'):
                action_end_date = action_start_date + timedelta(days=int(value))
            actions['end_date']= action_end_date
            actions['status'] = 0
            actions['created_on']= datetime.now()
            actions['updated_on']= datetime.now()
            action_id+=1
            action_start_date = action_end_date + timedelta(days=1)
        enabler_list = []
        enabler_id = 1
        for enabler in data['enablers']:
            enabler_list.append(
            {
                "enabler_id": enabler_id,
                "title": enabler,
                "progress": 0
            })
            enabler_id += 1
        data['enablers'] = enabler_list
    return new_data

'''find the milestone type'''
def find_mile_type(milestones,current_id,next_id):
    inter_list = []
    target_list = []
    if current_id == "current123":
        current_type = "milestone"
        for mile in milestones:
            if mile['milestone_id'] == next_id:
                next_type = mile['type']
                if next_type == 'intermediate_role':
                    inter_list.append(mile['intermediate_role'])
                else:
                    target_list.append(mile['targeted_role'])
    else:
        for mile in milestones:
            if mile['milestone_id'] == current_id:
                current_type = mile['type']
                if current_type == 'intermediate_role':
                    inter_list.append(mile['intermediate_role'])
                else:
                    target_list.append(mile['targeted_role'])
            if mile['milestone_id'] == next_id:
                next_type = mile['type']
                if next_type == 'intermediate_role':
                    inter_list.append(mile['intermediate_role'])
                else:
                    target_list.append(mile['targeted_role'])
    print(inter_list)
    print(target_list)
    if not target_list:
        target_list.append(milestones[len(milestones)-1]['targeted_role'])
    return current_type, next_type,inter_list,target_list

'''appends newly added intermediate role to the list'''
def append_new_intermediate(milestones,current_id,next_id,structured_add_intermediate):
    if current_id == "current123":
        current_id = milestones[0]['milestone_id']
    for idx,mile in enumerate(milestones):
        if mile['milestone_id'] == current_id:
            current_index = idx
        if mile['milestone_id'] == next_id:
            next_index = idx

    if current_index is not None and next_index is not None:
        milestones = milestones[:current_index] + structured_add_intermediate + milestones[next_index + 1:]
    return milestones

'''restructures select user journey for prompts'''
def nodemap_journey(current_role, nodemap):
    intermediate_roles = []
    for node in nodemap:
        if node["type"] == "intermediate_role":
            intermediate_roles.append({"milestone_id":node['milestone_id'],"title": node["title"]})
        if node["type"] == "targeted_role":
            sample = {
                "milestone_id" : node['milestone_id'],
                "title": node['title'],
             
            }
    new_structure = {
        "current_role": current_role['role'],
        "intermediate_roles": intermediate_roles,
        "targeted_role": sample
    }
    return new_structure

'''calculates timeline for nodemap edits'''
def calculate_timeline(milestones,current_id,next_id,days_diff):
    start_summing = False
    timeline_sum = 0
    current_date = datetime.now()
    if current_id == "current123":
        current_id = milestones[0]['milestone_id']
        current_id_start_date = milestones[0]['start_date']
        if current_id_start_date < current_date - timedelta(days=1):
            current_id_start_date = current_date
    for milestone in milestones:
        if milestone['milestone_id'] == current_id:
            start_summing = True
            current_id_start_date = milestone['start_date']
            if current_id_start_date < current_date - timedelta(days=1):
                current_id_start_date = current_date
        if start_summing:
            duration = milestone.get('timeline', 0)
            value = str(duration).split(' ')[0]
            timeline_sum += int(value)
        if milestone['milestone_id'] == next_id:
            break
    timeline_sum += days_diff
    return timeline_sum,current_id_start_date

'''Add Intermediate prompt'''
def add_intermediate(current_title,current_type,new_title,new_type,next_title,next_type,total_timeline,path_1,path_2,new_title_rank):
    response_1 = pd.read_excel(path_1).to_json(orient="records")
    milestone_1 = json.loads(response_1)
    response_2 = pd.read_excel(path_2).to_json(orient="records")
    milestone_2 = json.loads(response_2)
    
    #adding intermediate between current and NS
    if current_type == 'milestone' and next_type == 'targeted_role':
        print("adding intermediate between current and NS")
        query = f"""My current_role is {current_title} and I want to become a {next_title} by achieving through this {new_title_rank} {new_title}. (# root key ‘milestones’) .
        Note : The hierarchy should be : For the transition from {current_title} of type {current_type} to {new_title_rank} {new_title} of type {new_type} suggest me some minimum of 2 milestones necessary to achieve {new_title}. Then include {new_title} as a next milestone of type {new_type}.Then for the transition from {new_title_rank} {new_title} of type {new_type} to {next_title} of type {next_type} suggest me some minimum of 2 milestones necessary to achieve {next_title}. Then include {next_title} as a next milestone of type {next_type}(# root key ‘milestones’)  
        For each milestone, provide the following details:
        1. Title (key: 'title'): Ensure the milestone 'title' to be very specific related to the actions and not the role name(#max 100 characters).
        2. Milestone Description (key: 'milestone_description'): Describe the milestone.
        3. Milestone Type (key: 'type' value:'milestone' or 'intermediate_role' or 'targeted_role'.
        4. Actions (key: 'actions'): Suggest up to maximum 5 actions to achieve the milestone.
        5.From {milestone_1} analyse milestone['milestone_category'] and milestone['actions_to_track_and_complete'] details into consideration while generating the milestones and actions for a milestone(Please do not return these  milestone['milestone_category'] and milestone['actions_to_track_and_complete'] value in milestone 'title' and action 'title' response). But specify the milestone category(Key:'category') to which each milestones belong to.
        6.consider the type 'intermediate_role' and 'targeted_role' to be one among the suggested milestones(#except the fact that title(#max 100 characters) for these alone should be the role name without mentioning {new_title_rank} before the 'title') and actions 'title'(#max 150 characters) under this milestone 'title' be like from {milestone_2} milestone['milestone_category']). I want you to Divide the total timeline(key:‘timeline’ format: X day(s) #include this key for each milestone,this should sum up the action duration) of {total_timeline} day(s) suitably across each milestones.For each milestone, allocate a duration for each action (key: 'duration' (format:X day(s) by dividing the ‘duration’ within the milestone ‘timeline’)). Also,provide the ’title’ (# specifying any online courses, platforms, projects, or institutes along with the title  that can help achieve the action)and ‘description’ for each action.
        Additionally, suggest up to three critical enablers (key: 'enablers') for each milestone, chosen from the following list: [Growth mindset, Self-discipline, Optimism, Proactivity, Reflective thinking, Self-awareness, Attitude, Strategic thinking, Goal-setting, Creativity, Analytical thinking, Financial literacy, Learning agility, Leadership, Adaptability, Flexibility, Cultural competence, Conflict resolution, Active listening, Decision-making, Relationship building, Feedback-seeking].
        Return the response in proper JSON format(# root key ‘milestones’) without any explanations."""
    
    #adding intermediate between current and IR
    elif current_type == 'milestone' and next_type == 'intermediate_role':
        print("adding intermediate between current and IR")
        query = f"""My current_role is {current_title} and I want to become a {next_title} by achieving through this {new_title_rank} {new_title}. (# root key ‘milestones’) .
        Note : The hierarchy should be : For the transition from {current_title} of type {current_type} to {new_title_rank} {new_title} of type {new_type} suggest me some minimum of 2 milestones necessary to achieve {new_title}. Then include {new_title} as a next milestone of type {new_type}.Then for the transition from {new_title_rank} {new_title} of type {new_type} to {next_title} of type {next_type} suggest me some minimum of 2 milestones necessary to achieve {next_title}. Then include {next_title} as a next milestone of type {next_type}(# root key ‘milestones’)  
        For each milestone, provide the following details:
        1. Title (key: 'title'): Ensure the milestone 'title' to be very specific related to the actions and not the role name(#max 100 characters).
        2. Milestone Description (key: 'milestone_description'): Describe the milestone.
        3. Milestone Type (key: 'type' value:'milestone' or 'intermediate_role'.
        4. Actions (key: 'actions'): Suggest up to maximum 5 actions to achieve the milestone.
        5.From {milestone_1} analyse milestone['milestone_category'] and milestone['actions_to_track_and_complete'] details into consideration while generating the milestones and actions for a milestone(Please do not return these  milestone['milestone_category'] and milestone['actions_to_track_and_complete'] value in milestone 'title' and action 'title' response). But specify the milestone category(Key:'category') to which each milestones belong to.
        6.consider the type 'intermediate_role' to be one among the suggested milestones(#except the fact that title(#max 100 characters) for these alone should be the role name without mentioning {new_title_rank} before the 'title') and actions 'title'(#max 150 characters) under this milestone 'title' be like from {milestone_2} milestone['milestone_category']). I want you to Divide the total timeline(key:‘timeline’ format: X day(s) #include this key for each milestone,this should sum up the action duration) of {total_timeline} day(s) suitably across each milestones.For each milestone, allocate a duration for each action (key: 'duration' (format:X day(s) by dividing the ‘duration’ within the milestone ‘timeline’)). Also,provide the ’title’ (# specifying any online courses, platforms, projects, or institutes along with the title  that can help achieve the action)and ‘description’ for each action.
        Additionally, suggest up to three critical enablers (key: 'enablers') for each milestone, chosen from the following list: [Growth mindset, Self-discipline, Optimism, Proactivity, Reflective thinking, Self-awareness, Attitude, Strategic thinking, Goal-setting, Creativity, Analytical thinking, Financial literacy, Learning agility, Leadership, Adaptability, Flexibility, Cultural competence, Conflict resolution, Active listening, Decision-making, Relationship building, Feedback-seeking].
        Return the response in proper JSON format(# root key ‘milestones’) without any explanations."""
    
    #adding intermediate between two IR
    elif current_type == 'intermediate_role' and next_type == 'intermediate_role' :
        print("adding intermediate between two IR")
        query = f"""My current_role is {current_title} and I want to become a {next_title} by achieving through this {new_title_rank} {new_title}. (# root key ‘milestones’) .
        Note: The hierarchy should be:Include {current_title} as the first milestone of type {current_type}. Then for the transition from {current_title} of type {current_type} to {new_title_rank} {new_title} of type {new_type} mandatorily suggest me minimum of 2 milestones to achieve {new_title}.Then include {new_title} as a next milestone of type {new_type}.Then for the transition from {new_title_rank} {new_title} of type {new_type} to {next_title} of type {next_type} mandatorily suggest me minimum of 2 milestones to achieve {next_title}. Then include {next_title} as a next milestone of type {next_type}(# root key ‘milestones’)  
        For each milestone, provide the following details:
        1. Title (key: 'title'): Ensure the milestone 'title' to be very specific related to the actions and not the role name(#max 100 characters).
        2. Milestone Description (key: 'milestone_description'): Describe the milestone.
        3. Milestone Type (key: 'type' value:'milestone' or 'intermediate_role').
        4. Actions (key: 'actions'): Suggest up to maximum 5 actions to achieve the milestone.
        5. From {milestone_1} analyse milestone['milestone_category'] and milestone['actions_to_track_and_complete'] details into consideration while generating the milestones and  while generating particular actions  for that milestone(Please do not return these  milestone['milestone_category'] and milestone['actions_to_track_and_complete'] value in milestone 'title' and action 'title' response). But specify the milestone category(Key:'category') to which each milestones belong to.
        6. consider the type 'intermediate_role' to be one among the suggested milestones(#except the fact that title(#max 100 characters) for these alone should be the role name without mentioning {new_title_rank} before the 'title' and actions 'title'(#max 150 characters) under this milestone 'title' be like from {milestone_2} milestone['milestone_category'].I want you to Divide the total timeline(key:‘timeline’ format: X day(s) #include this key for each milestone,this should sum up the action duration) of {total_timeline} day(s) suitably across each milestones.For each milestone, allocate a duration for each action (key: 'duration' (format:X day(s) by dividing the ‘duration’ within the milestone ‘timeline’)). Also,provide the ’title’ (# specifying any online courses, platforms, projects, or institutes along with the title  that can help achieve the action)and ‘description’ for each action.
        Additionally, suggest up to three critical enablers (key: 'enablers') for each milestone, chosen from the following list: [Growth mindset, Self-discipline, Optimism, Proactivity, Reflective thinking, Self-awareness, Attitude, Strategic thinking, Goal-setting, Creativity, Analytical thinking, Financial literacy, Learning agility, Leadership, Adaptability, Flexibility, Cultural competence, Conflict resolution, Active listening, Decision-making, Relationship building, Feedback-seeking].
        Please return the response in JSON format(# root key ‘milestones’) without any explanations."""

    #adding intermediate between IR and NS
    else:
        print("adding intermediate between IR and NS")
        query = f"""My current_role is {current_title} and I want to become a {next_title} by achieving through this {new_title_rank} {new_title}. (# root key ‘milestones’) .
        Note: The hierarchy should be:Include {current_title} as the first milestone of type {current_type}. Then for the transition from {current_title} of type {current_type} to {new_title_rank} {new_title} of type {new_type} mandatorily suggest me minimum of 2 milestones to achieve {new_title}.Then include {new_title} as a next milestone of type {new_type}.Then for the transition from {new_title_rank} {new_title} of type {new_type} to {next_title} of type {next_type} mandatorily suggest me minimum of 2 milestones to achieve {next_title}. Then include {next_title} as a next milestone of type {next_type}(# root key ‘milestones’)  
        For each milestone, provide the following details:
        1. Title (key: 'title'): Ensure the milestone 'title' to be very specific related to the actions and not the role name(#max 100 characters).
        2. Milestone Description (key: 'milestone_description'): Describe the milestone.
        3. Milestone Type (key: 'type' value:'milestone' or 'intermediate_role' or 'targeted_role'.
        4. Actions (key: 'actions'): Suggest up to maximum 5 actions to achieve the milestone.
        5. From {milestone_1} analyse milestone['milestone_category'] and milestone['actions_to_track_and_complete'] details into consideration while generating the milestones and  while generating particular actions  for that milestone(Please do not return these  milestone['milestone_category'] and milestone['actions_to_track_and_complete'] value in milestone 'title' and action 'title' response). But specify the milestone category(Key:'category') to which each milestones belong to.
        6. consider the type 'intermediate_role' and 'targeted_role' to be one among the suggested milestones(#except the fact that title(#max 100 characters) for these alone should be the role name and actions 'title'(#max 150 characters) under this milestone 'title' be like from {milestone_2} milestone['milestone_category']).I want you to Divide the total timeline(key:‘timeline’ format: X day(s) #include this key for each milestone,this should sum up the action duration) of {total_timeline} day(s) suitably across each milestones.For each milestone, allocate a duration for each action (key: 'duration' (format:X day(s) by dividing the ‘duration’ within the milestone ‘timeline’)). Also,provide the ’title’ (# specifying any online courses, platforms, projects, or institutes along with the title  that can help achieve the action)and ‘description’ for each action.
        Additionally, suggest up to three critical enablers (key: 'enablers') for each milestone, chosen from the following list: [Growth mindset, Self-discipline, Optimism, Proactivity, Reflective thinking, Self-awareness, Attitude, Strategic thinking, Goal-setting, Creativity, Analytical thinking, Financial literacy, Learning agility, Leadership, Adaptability, Flexibility, Cultural competence, Conflict resolution, Active listening, Decision-making, Relationship building, Feedback-seeking].
        Please return the response in JSON format(# root key ‘milestones’) without any explanations."""
    
    
    llm = ChatOpenAI(model="gpt-4",temperature=0.18)
    prompt = PromptTemplate(
    input_variables=["job_recommend"],
    template = "{job_recommend}"
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    with get_openai_callback() as cb:
        response = chain.run({
                            "job_recommend":query
                            })
    tokens = {
            "Total Tokens": cb.total_tokens,
            "Prompt Tokens": cb.prompt_tokens,
            "Completion Tokens": cb.completion_tokens,
            "Total Cost (USD)": f"${cb.total_cost}"
        }
    print(tokens)
    response = json.loads(response)
    return response, tokens['Total Cost (USD)']

'''Edit NS prompt'''
def north_star_milestone(current_role,old_target_title,new_target_rank,new_target_title,career_path_list,timeline,path_1,path_2):
    response_1 = pd.read_excel(path_1).to_json(orient="records")
    milestone_1 = json.loads(response_1)
    response_2 = pd.read_excel(path_2).to_json(orient="records")
    milestone_2 = json.loads(response_2)
    query = f""" My current role is {current_role}. To achieve my target role {old_target_title} I have completed few milestones and actions mentioned in the given career path list: {career_path_list}. Now I wish to change my career path to {new_target_rank} {new_target_title}. 
    As a professional expert suggest me some milestones and actions to resume my career path to achieve my goal of becoming {new_target_rank} {new_target_title} in a timeline of {timeline} day(s) by not repeating the ones in the career_path list: {career_path_list}.
    If required, suggest me some suitable intermediate roles and actions to achieve the intermediate_role to brigde the gap to help me reach my goal of becoming a {new_target_rank} {new_target_title}. Note :The hierarchy should be: milestones to reach intermediate_role,then intermediate_role itself,milestones to achieve targeted_role,then targeted_role itself.
    If you suggest intermediate_role, then specify its Sector (key:'sector'), specific Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to(key:'domain'),type of company (key:'company_type'), and hierarchy level (key:'rank'#Please return only the level(Eg. senior/junior/principal etc accordingly) and not the 'role') within the key name('role_details').
    For each milestone, provide the following details:
        1. Title (key: 'title'): Ensure the milestone 'title' to be very specific related to the actions and not the role name(#max 100 characters).
        2. Milestone Description (key: 'milestone_description'): Describe the milestone.
        3. Milestone Type (key: 'type' value:'milestone' or 'intermediate_role' or 'targeted_role'.
        4. Actions (key: 'actions'): Suggest up to maximum 5 actions to achieve the milestone.
        5. From {milestone_1} analyse milestone['milestone_category'] and milestone['actions_to_track_and_complete'] details into consideration while generating the milestones and  while generating particular actions  for that milestone(Please do not return these  milestone['milestone_category'] and milestone['actions_to_track_and_complete'] value in milestone 'title' and action 'title' response). But specify the milestone category(Key:'category') to which each milestones belong to.
        6. consider the type 'intermediate_role' and 'targeted_role' to be one among the suggested milestones(#except the fact that title(#max 100 characters) for these alone should be the role name and actions 'title'(#max 150 characters) under this milestone 'title' be like from {milestone_2} milestone['milestone_category']).I want you to Divide the total timeline(key:‘timeline’ format: X day(s) #include this key for each milestone,this should sum up the action duration) of {timeline} day(s) suitably across each milestones. For each milestone, allocate a duration for each action (key: 'duration' (format:X day(s) by dividing the ‘duration’ within the milestone ‘timeline’)). Also,provide the ’title’ (# specifying any online courses, platforms, projects, or institutes along with the title  that can help achieve the action)and ‘description’ for each action.
        Additionally, suggest up to three critical enablers(key:'enablers') for each milestone, chosen from the following list: [Growth mindset, Self-discipline, Optimism, Proactivity, Reflective thinking, Self-awareness, Attitude, Strategic thinking, Goal-setting, Creativity, Analytical thinking, Financial literacy, Learning agility, Leadership, Adaptability, Flexibility, Cultural competence, Conflict resolution, Active listening, Decision-making, Relationship building, Feedback-seeking].
        Please return the response in JSON format(# root key ‘milestones’) without any explanations."""
    
    llm = ChatOpenAI(model="gpt-4",temperature=0.18)
    prompt = PromptTemplate(
    input_variables=["job_recommend"],
    template = "{job_recommend}"
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    with get_openai_callback() as cb:
        response = chain.run({
                            "job_recommend":query
                            })
    tokens = {
            "Total Tokens": cb.total_tokens,
            "Prompt Tokens": cb.prompt_tokens,
            "Completion Tokens": cb.completion_tokens,
            "Total Cost (USD)": f"${cb.total_cost}"
        }
    print(tokens)
    response = json.loads(response)
    return response, tokens['Total Cost (USD)']

'''Edit NS restructuring'''
def new_target_nodemap(new_milestones,last_end_date,target_list):
    start_date = last_end_date + timedelta(days=1)
    for data in new_milestones:
        if data['type'] == 'intermediate_role':
            data['intermediate_role'] = data.pop('role_details')
        if data['type'] == 'targeted_role':
            if 'role_details' in data:
                data.pop('role_details')
                data['targeted_role'] = target_list
            else:
                data['targeted_role'] = target_list

        data['milestone_id'] = str(uuid.uuid4())
        data['progress'] = 0 
        data['start_date']= start_date
        action_start_date = start_date
        duration = data['timeline']
        value = str(duration).split(' ')[0]
        if str(duration).__contains__('day'):
            end_date = start_date + timedelta(days=int(value))
        data['end_date']= end_date
        data['created_on']= datetime.now()
        data['updated_on']= datetime.now()
        start_date = end_date + timedelta(days=1)
        action_id = 1
        for actions in data['actions']:
            actions['action_id'] = action_id
            actions['start_date'] = action_start_date
            duration = actions['duration']
            value = str(duration).split(' ')[0]
            if str(duration).__contains__('day'):
                action_end_date = action_start_date + timedelta(days=int(value))
            actions['end_date']= action_end_date
            actions['status'] = 0
            actions['created_on']= datetime.now()
            actions['updated_on']= datetime.now()
            action_id+=1
            action_start_date = action_end_date + timedelta(days=1)
        enabler_list = []
        enabler_id = 1
        for enabler in data['enablers']:
            enabler_list.append(
            {
                "enabler_id": enabler_id,
                "title": enabler,
                "progress": 0
            })
            enabler_id += 1
        data['enablers'] = enabler_list
    return new_milestones

'''Edit Ns : when NS action in progress prompt'''
def north_star_progress_milestone(current_role,old_target_title,target_rank,new_target_title,career_path_list,timeline,path_1,path_2):
    response_1 = pd.read_excel(path_1).to_json(orient="records")
    milestone_1 = json.loads(response_1)
    response_2 = pd.read_excel(path_2).to_json(orient="records")
    milestone_2 = json.loads(response_2)
    new_type = "targeted_role"
    query = f""" My current role is {current_role}. To achieve my target role {old_target_title} I have completed few milestones and actions mentioned in the given career path list: {career_path_list}. Now I wish to change my career path to {new_target_title}. 
    As a professional expert suggest me some milestones and actions to resume my career path to achieve my goal of becoming {new_target_title} in a timeline of {timeline} day(s) by not repeating the ones in the career_path list: {career_path_list}
    Note : The hierarchy should be : For the transition from {current_role} to {target_rank} {new_target_title} suggest me some milestones necessary to achieve {target_rank} {new_target_title}. Then include {new_target_title} as a next milestone of type {new_type}.(# root key ‘milestones’)  
    For each milestone, provide the following details:
        1. Title (key: 'title'): Ensure the milestone 'title' to be very specific related to the actions and not the role name(#max 100 characters).
        2. Milestone Description (key: 'milestone_description'): Describe the milestone.
        3. Milestone Type (key: 'type' value:'milestone' or 'targeted_role'.
        4. Actions (key: 'actions'): Suggest up to maximum 5 actions to achieve the milestone.
        5. From {milestone_1} analyse milestone['milestone_category'] and milestone['actions_to_track_and_complete'] details into consideration while generating the milestones and  while generating particular actions  for that milestone(Please do not return these  milestone['milestone_category'] and milestone['actions_to_track_and_complete'] value in milestone 'title' and action 'title' response). But specify the milestone category(Key:'category') to which each milestones belong to.
        6. consider the type 'targeted_role' to be one among the suggested milestones(#except the fact that title(#max 100 characters) for these alone should be the role name and actions 'title'(#max 150 characters) under this milestone 'title' be like from {milestone_2} milestone['milestone_category']).I want you to Divide the total timeline(key:‘timeline’ format: X day(s) #include this key for each milestone,this should sum up the action duration) of {timeline} day(s) suitably across each milestones. For each milestone, allocate a duration for each action (key: 'duration' (format:X day(s) by dividing the ‘duration’ within the milestone ‘timeline’)). Also,provide the ’title’ (# specifying any online courses, platforms, projects, or institutes along with the title  that can help achieve the action)and ‘description’ for each action.
        Additionally, suggest up to three critical enablers(key:'enablers') for each milestone, chosen from the following list: [Growth mindset, Self-discipline, Optimism, Proactivity, Reflective thinking, Self-awareness, Attitude, Strategic thinking, Goal-setting, Creativity, Analytical thinking, Financial literacy, Learning agility, Leadership, Adaptability, Flexibility, Cultural competence, Conflict resolution, Active listening, Decision-making, Relationship building, Feedback-seeking].
        Please return the response in JSON format(# root key ‘milestones’) without any explanations."""
    
    
    llm = ChatOpenAI(model="gpt-4",temperature=0.18)
    prompt = PromptTemplate(
    input_variables=["job_recommend"],
    template = "{job_recommend}"
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    with get_openai_callback() as cb:
        response = chain.run({
                            "job_recommend":query
                            })
    tokens = {
            "Total Tokens": cb.total_tokens,
            "Prompt Tokens": cb.prompt_tokens,
            "Completion Tokens": cb.completion_tokens,
            "Total Cost (USD)": f"${cb.total_cost}"
        }
    print(tokens)
    response = json.loads(response)
    return response, tokens['Total Cost (USD)']

'''Edit Ns : when NS action in progress restructuring'''
def north_star_progress_restructure(new_milestones,last_end_date,target_list):
    start_date = last_end_date + timedelta(days=1)
    for data in new_milestones:
        if data['type'] == 'targeted_role':
            data['targeted_role'] = target_list

        data['milestone_id'] = str(uuid.uuid4())
        data['progress'] = 0 
        data['start_date']= start_date
        action_start_date = start_date
        duration = data['timeline']
        value = str(duration).split(' ')[0]
        if str(duration).__contains__('day'):
            end_date = start_date + timedelta(days=int(value))
        data['end_date']= end_date
        data['created_on']= datetime.now()
        data['updated_on']= datetime.now()
        start_date = end_date + timedelta(days=1)
        action_id = 1
        for actions in data['actions']:
            actions['action_id'] = action_id
            actions['start_date'] = action_start_date
            duration = actions['duration']
            value = str(duration).split(' ')[0]
            if str(duration).__contains__('day'):
                action_end_date = action_start_date + timedelta(days=int(value))
            actions['end_date']= action_end_date
            actions['status'] = 0
            actions['created_on']= datetime.now()
            actions['updated_on']= datetime.now()
            action_id+=1
            action_start_date = action_end_date + timedelta(days=1)
        enabler_list = []
        enabler_id = 1
        for enabler in data['enablers']:
            enabler_list.append(
            {
                "enabler_id": enabler_id,
                "title": enabler,
                "progress": 0
            })
            enabler_id += 1
        data['enablers'] = enabler_list
    return new_milestones