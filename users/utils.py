from django.template.loader import render_to_string
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.contrib.auth.hashers import make_password
import string
import random
# from users.models import Milestones,Milestones_Actions,Milestones_Enablers
from datetime import timedelta,date
from datetime import datetime


def hash_password(password):
    return make_password(password)


def generate_otp(length):
    letters = string.ascii_letters
    digits = string.digits
    otp = random.choice(letters) + random.choice(digits)
    otp += ''.join(random.choice(letters + digits) for _ in range(length - 2))
    otp_list = list(otp)
    random.shuffle(otp_list)
    otp = ''.join(otp_list)
    return otp


'''Email API with out template'''
def send_emails(subject, to_email, content):

    email_from = settings.DEFAULT_FROM_EMAIL
    recipient_list = [to_email]
    message = EmailMessage(subject, content, email_from, recipient_list)
    message.content_subtype = 'html'
    message.send()

def send_template_emails(subject,to_email,html,mydict):
    subject = subject
    html_template = html
    html_message = render_to_string(html_template, context=mydict)
    email_from = settings.DEFAULT_FROM_EMAIL
    recipient_list = [to_email]
    message = EmailMessage(subject, html_message,
                           email_from, recipient_list)
    message.content_subtype = 'html'
    message.send()



def parse_timeline(timeline):
    # Split the timeline string into parts (e.g., "1", "year")
    parts = timeline.split()
    if len(parts) != 2:
        raise ValueError("Invalid timeline format. Please use 'X year(s)' or 'X month(s)'.")

    # Convert the numerical part to float
    num = float(parts[0])

    # Determine the unit (year or month)
    unit = parts[1].lower()
    if unit == "year" or unit == "years":
        return timedelta(days=num * 365.25)  
    elif unit == "month" or unit == "months":
        return timedelta(days=num * 30.44) 
    else:
        raise ValueError("Invalid unit in timeline. Please use 'year(s)' or 'month(s)'.")

def date_calc(start_date,timeline):
    duration = parse_timeline(timeline)
    end_date = start_date + duration
    return end_date


def calculate_experience_duration(start_date, end_date=None):
        # Convert the start_date and end_date to datetime objects
        # start_date = datetime.strptime(start_date, "%B %Y")
        # end_date = datetime.now() if end_date.lower() == "present" else datetime.strptime(end_date, "%B %Y")
        # #end_date = datetime.strptime(end_date, "%B %Y") if end_date else datetime.now()
        if start_date and start_date.lower() != "null":
            start_date = datetime.strptime(start_date, "%B %Y")
        else:
            start_date = datetime.now()
        end_date = datetime.now() if end_date.lower() == "present" else datetime.strptime(end_date, "%B %Y")

        # Calculate the difference in years and months
        delta = end_date - start_date
        years = delta.days // 365
        remaining_days = delta.days % 365
        months = remaining_days // 30

        # Return the formatted experience duration
        if years == 0 and months == 1:
            return "1 month"
        elif years == 0:
            return f"{months} months"
        elif years == 1 and months == 0:
            return "1 year"
        elif years > 0 and months == 0:
            return f"{years} year{'s' if years > 1 else ''}"  # Use 'year' for singular, 'years' for plural
        else:
            return f"{years} year{'s' if years > 1 else ''} {months} month{'s' if months > 1 else ''}"
    

def calculate_duration(start_date, end_date=None):
    if start_date and end_date:
        # Convert the start_date and end_date to datetime objects
        start_date = datetime.strptime(start_date, "%B %Y")
        end_date = datetime.now() if end_date.lower() == "present" else datetime.strptime(end_date, "%B %Y")

        # Calculate the difference in years and months
        delta = end_date - start_date
        years = delta.days // 365
        remaining_days = delta.days % 365
        months = remaining_days // 30

        # Return the formatted experience duration
        if years == 0 and months == 1:
            return "1 month"
        elif years == 0:
            return f"{months} months"
        elif years == 1 and months == 0:
            return "1 year"
        elif years > 0 and months == 0:
            return f"{years} year{'s' if years > 1 else ''}"  # Use 'year' for singular, 'years' for plural
        else:
            return f"{years} year{'s' if years > 1 else ''} {months} month{'s' if months > 1 else ''}"
    else:
        return "N/A"


def calculate_redirect_step(user_data, onboarding_status):
    questionnaire=user_data.get("questionnaire", {})
    if questionnaire:
        question_3_response = questionnaire.get("clear_vision_for_next_career_runway")
        duration = user_data.get("questionnaire", {}).get("career_runway_duration")
        role = user_data.get("questionnaire", {}).get("consider_intermediate_role")
        
        if onboarding_status == 5:
            # Check the response of the yes/no question and duration
            

            if question_3_response == True and duration < 24:
                return 7  # Navigate to questionnaire 4
            elif question_3_response == True and duration >= 24:
                return 6  # Navigate to Intermediate Role, further to Questionnaire 4
            elif question_3_response == False and duration < 24:
                return 8  # Navigate to Runway Recommendations
            elif question_3_response == False and duration >= 24:
                return 6  # Navigate to Intermediate Role, further to Runway Recommendations
        if onboarding_status == 6:
            
            if question_3_response == False and duration >= 24:
                return 8  # Navigate to Runway Recommendations
        if duration:
            if duration >=24 and role == "":
                return 6

    return onboarding_status + 1


def onboarding_status_fun(onboarding_status):
    
        if onboarding_status == 8:
                return 2  # Navigate to Intermediate Role, further to Runway Recommendations
        elif onboarding_status != 8:
            
                return 1  # Navigate to Runway Recommendations

def singup_type_func(signup_type):
    if signup_type == 'email':
        return False
    else:
        return True