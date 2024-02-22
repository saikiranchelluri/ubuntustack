from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
import uuid
import calendar




def convert_date(date):
    if date is None:
        return None
    month_name = calendar.month_name[date["month"]]
    return f"{month_name} {date['year']}"



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
            fields_to_remove = ["school_linkedin_profile_url", "logo_url", "grade", "activities_and_societies","description"]
            for field in fields_to_remove:
                if field in education:
                    education.pop(field, None)
            if "field_of_study" in education:
                specialization_value = education.pop("field_of_study")
                education["specialization"] = specialization_value

            if "degree_name" in education:
                education["degree"] = education.pop("degree_name")

        # Change key name "school" to "university"
            if "school" in education:
                education["university"] = education.pop("school")
            education["id"] = unique_id
            education["retrieved_from"]= "Linkedin"
            education ["updated_at"] =datetime.now()
            education["created_at"]=datetime.now()
            end_date = education["ends_at"]
            education["end_date"] = convert_date(end_date)
            start_date = education["starts_at"]
            education["start_date"] = convert_date(start_date)
            del education["starts_at"]
            del education["ends_at"]
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
            fields_to_remove = ["company_linkedin_profile_url", "logo_url", "location","description"]
            for field in fields_to_remove:
                if field in experience:
                    experience.pop(field, None)
            if "title" in experience:
                specialization_value = experience.pop("title")
                experience["role"] = specialization_value
            experience["id"] = unique_id
            experience["retrieved_from"]= "Linkedin"
            experience ["updated_at"] =datetime.now()
            experience["created_at"]=datetime.now()
            end_date = experience["ends_at"]
            experience["end_date"] = convert_date(end_date)
            start_date = experience["starts_at"]
            experience["start_date"] = convert_date(start_date)
            del experience["starts_at"]
            del experience["ends_at"]
            unique_id += 1
    return work_experience



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
            fields_to_remove = ["license_number", "url", "display_source", "ends_at"]
            for field in fields_to_remove:
                if field in each_certification:
                    each_certification.pop(field, None)
            if "name" in each_certification:
                specialization_value = each_certification.pop("name")
                each_certification["title"] = specialization_value

            if "authority" in each_certification:
                each_certification["from_organization"] = each_certification.pop("authority")

            each_certification["id"] = unique_id
            each_certification["retrieved_from"]= "Linkedin"
            each_certification ["updated_at"] =datetime.now()
            each_certification["created_at"]=datetime.now()
            end_date = each_certification["starts_at"]
            each_certification["exhibited_on"] = convert_date(end_date)
            del each_certification["starts_at"]
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
            if "issuer" in each_achievement:
                specialization_value = each_achievement.pop("issuer")
                each_achievement["from_organization"] = specialization_value
            each_achievement["id"] = unique_id
            each_achievement["retrieved_from"]= "Linkedin"
            each_achievement ["updated_at"] =datetime.now()
            each_achievement["created_at"]=datetime.now()
            end_date = each_achievement["issued_on"]
            each_achievement["exhibited_on"] = convert_date(end_date)
            del each_achievement["issued_on"]
            
            unique_id += 1
    return achievements







