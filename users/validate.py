from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
import uuid







def validate_date_format(date_string):
        if date_string == None:
            return None
        if date_string.lower() == "present":
            return date_string
        try:
            datetime.strptime(date_string, "%B %Y")
            return date_string
        except ValueError:
            return None

def validate_education(education_levels):
    if education_levels is None or ((isinstance(education_levels,list)) and len(education_levels)==0):
        education_levels = None
    elif education_levels is not None:
        if isinstance(education_levels,dict):
            edu = []
            edu.append(education_levels)
            education_levels = edu
        unique_id = 1
        for education in education_levels:
            education["id"] = unique_id
            education["retrieved_from"]= "resume"
            education ["updated_at"] =datetime.now()
            education["created_at"]=datetime.now()
            end_date = education["end_date"]
            education["end_date"] = validate_date_format(end_date)
            start_date = education["start_date"]
            education["start_date"] = validate_date_format(start_date)
            unique_id += 1
    return education_levels

def validate_experience(work_experience):
    if work_experience is None or ((isinstance(work_experience,list)) and len(work_experience)==0):
       work_experience = None
    elif work_experience is not None:
        if isinstance(work_experience,dict):
            exp = []
            exp.append(work_experience)
            work_experience = exp
        unique_id = 1
        for experience in work_experience:
            experience["id"] = unique_id
            experience["retrieved_from"]= "resume"
            experience ["updated_at"] =datetime.now()
            experience["created_at"]=datetime.now()
            end_date = experience["end_date"]
            experience["end_date"] = validate_date_format(end_date)
            start_date = experience["start_date"]
            experience["start_date"] = validate_date_format(start_date)
            unique_id += 1
            if isinstance(experience["tech_skills"],list) and len(experience["tech_skills"])==0:
                experience["tech_skills"] = None
    return work_experience


def validate_professional_associations(associations):
    if associations is None or ((isinstance(associations,list)) and len(associations)==0):
       associations = None
    elif associations is not None:
        if isinstance(associations,dict):
            associate = []
            associate.append(associations)
            associations = associate
        unique_id = 1
        for each_association in associations:
            each_association["id"] = unique_id
            each_association["retrieved_from"]= "resume"
            each_association ["updated_at"] =datetime.now()
            each_association["created_at"]=datetime.now()
            end_date = each_association["end_date"]
            each_association["end_date"] = validate_date_format(end_date)
            start_date = each_association["start_date"]
            each_association["start_date"] = validate_date_format(start_date)
            unique_id += 1
    return associations

def validate_certifications(certifications):
    if certifications is None or ((isinstance(certifications,list)) and len(certifications)==0):
       certifications = None
    elif certifications is not None:
        if isinstance(certifications,dict):
            certify = []
            certify.append(certifications)
            certifications = certify
        unique_id = 1
        for each_certification in certifications:
            each_certification["id"] = unique_id
            each_certification["retrieved_from"]= "resume"
            each_certification ["updated_at"] =datetime.now()
            each_certification["created_at"]=datetime.now()
            end_date = each_certification["exhibited_on"]
            each_certification["exhibited_on"] = validate_date_format(end_date)
            unique_id += 1
    return certifications

def validate_achievements(achievements):
    if achievements is None or ((isinstance(achievements,list)) and len(achievements)==0):
       achievements = None
    elif achievements is not None:
        if isinstance(achievements,dict):
            achieve = []
            achieve.append(achievements)
            achievements = achieve
        unique_id = 1
        for each_achievement in achievements:
            each_achievement["id"] = unique_id
            each_achievement["retrieved_from"]= "resume"
            each_achievement ["updated_at"] =datetime.now()
            each_achievement["created_at"]=datetime.now()
            end_date = each_achievement["exhibited_on"]
            each_achievement["exhibited_on"] = validate_date_format(end_date)
            unique_id += 1
    return achievements


def validate_soft_skills(soft_skills):
    if soft_skills is None or ((isinstance(soft_skills,list)) and len(soft_skills)==0):
       soft_skills = []
    elif soft_skills is not None:
        if isinstance(soft_skills,str):
            ss = soft_skills.split(',')
            soft_skills = ss
        if isinstance(soft_skills,dict):
            soft_skills = list(soft_skills.values())
            soft_skills ["updated_at"] =datetime.now()
            soft_skills["created_at"]=datetime.now()
    return soft_skills


def validate_hobbies(hobbies):
    if hobbies is None or ((isinstance(hobbies,list)) and len(hobbies)==0):
       hobbies = []
    elif hobbies is not None:
        if isinstance(hobbies,str):
            hs = hobbies.split(',')
            hobbies = hs
        if isinstance(hobbies,dict):
            hobbies = list(hobbies.values())
            hobbies ["updated_at"] =datetime.now()
            hobbies["created_at"]=datetime.now()
    return hobbies

def restructure_nodemap(nodemap_structure,user_id,selected_user_journey):
    start_date = datetime.now()
    n=0
    for mile in nodemap_structure:
        if mile['type'] == "targeted_role":
            selected_user_journey['targeted_role'].pop('role')
            mile['targeted_role'] = selected_user_journey["targeted_role"]
        
        if mile['type'] == "intermediate_role":
            selected_user_journey['intermediate_roles'][n].pop('role')
            mile['intermediate_role'] = selected_user_journey["intermediate_roles"][n]
            n=n+1
        mile['milestone_id'] = str(uuid.uuid4())
        mile['progress'] = 0
        mile['start_date']= start_date
        action_start_date = start_date
        duration = mile['timeline']
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
        mile['end_date']= end_date
        mile['created_on']= datetime.now()
        mile['updated_on']= datetime.now()
        start_date = end_date + timedelta(days=1)
        act_id = 1
        for act in mile['actions']:
                act['action_id'] = act_id
                act['start_date'] = action_start_date
                duration = act['duration']
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
                act['end_date']= action_end_date
                act['created_on']= datetime.now()
                act['updated_on']= datetime.now()
                act['status'] = 0
                act_id += 1
                action_start_date = action_end_date + timedelta(days=1)
        enabler_id = 1
        enabler_list = []
        for enabler in mile['enablers']:
            enabler_list.append(
            {
                "enabler_id": enabler_id,
                "title": enabler,
                "progress": 0
            })
            enabler_id += 1
        mile['enablers'] = enabler_list
        new_structure ={
            "user_id" : str(user_id),
            "milestones": nodemap_structure
        }
    return new_structure



def restructure_job_recommendation(response):
    restructured_career_paths = []
    for career_path in response["career_paths"]:
        if "intermediate_roles" not in career_path:
            career_path["intermediate_roles"] = []
        if "intermediate_roles" in career_path and isinstance(career_path["intermediate_roles"], dict):                    
            ir = []
            ir.append(career_path["intermediate_roles"])
            career_path["intermediate_roles"] = ir
        restructured_res_data = {
                "targeted_role": {
                    key: value for key, value in career_path.items() if key != "intermediate_roles"
                },
                "intermediate_roles": career_path["intermediate_roles"]
            }
        restructured_career_paths.append(restructured_res_data)
    restructured_res_data = {"career_paths": restructured_career_paths}
    return restructured_res_data