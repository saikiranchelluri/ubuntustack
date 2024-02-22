from django.shortcuts import render
from urllib.parse import urlsplit
from django.views.decorators.csrf import csrf_exempt
import secrets
from django.contrib.auth.hashers import make_password,check_password
from dateutil.relativedelta import relativedelta
from django.contrib.sessions.backends.db import SessionStore
from bson import ObjectId
import datetime
from users.redis_connection import redis_client,redis_client_update_number,redis_client_update_email,redis_client_update_password,redis_client_update_2FA
from users.mongoDb_connection import users_registration,userLogin_Details,resume_data,dashboard_data,billing_details,nudges,nudge_preference,payments_collection,subscriptions_collection,phone_codes,\
    industry,function,Cost_Details
from django.http import request
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.callbacks import get_openai_callback
import os
from users.validate import validate_achievements,validate_certifications,validate_education,validate_experience,validate_hobbies,validate_professional_associations,validate_soft_skills,restructure_nodemap
from openai.error import ServiceUnavailableError,InvalidRequestError,RateLimitError
from users.chatgpt import resume_reader
from users.utils import generate_otp,send_emails,hash_password,calculate_experience_duration,calculate_duration,calculate_redirect_step,onboarding_status_fun,singup_type_func,send_template_emails
from rest_framework.response import Response
from django.core.files.storage import default_storage
from urllib.parse import urljoin
from operator import itemgetter
from users.validate import restructure_job_recommendation
from django.http import JsonResponse
from django.core.paginator import Paginator
from bson import json_util
import re
from rest_framework.views import APIView
import json
from rest_framework import status,generics
from youe_backend import settings
# from django.conf import settings
from django.utils.encoding import smart_str, force_bytes, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
import bson
from django.db import transaction
import pandas as pd
from youe_backend.settings import base_url
import boto3
from django.core.files.base import ContentFile
from storages.backends.s3boto3 import S3Boto3Storage
# Create your views here.
'''User Registration'''
class userRegister(APIView):
    
    def post(self, request):
        request_body = request.data  # Use request.data to parse JSON data
        email = request_body.get("email")
        password = request_body.get("password")

        if not email or not password:
            return Response({"message": "Email and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        existing_user = users_registration.find_one({"email": email})
        
        if existing_user is None:

            hashed_password = make_password(password)
            
            user_data = {
                "email": email,
                "updated_at": datetime.datetime.now(),
                "last_login": datetime.datetime.now(),
                "created_on": datetime.datetime.now(),
                "signup_type": "email",
                "email_verified": True,
                "2fa": False,
                "password": hashed_password,
                "onboarding_process":{"step":0,"process":"setup password"}
            }

                # Update the user data in the database
            user_id = users_registration.insert_one(user_data).inserted_id
            print(user_id)
            return Response({"message": "Password created successfully", "user_id": str(user_id)},status=status.HTTP_200_OK)
            # User with the same email already exists, return an error response
        else:
            
            user_id = str(existing_user["_id"])
            onboarding_process = existing_user.get("onboarding_process")
            if onboarding_process is None:
                return Response({"message": "Onboarding process information not found"}, status=status.HTTP_400_BAD_REQUEST)
            onboarding_status = onboarding_process.get("step")
            onboarding_step= onboarding_status_fun(onboarding_status)
            redirect_step = calculate_redirect_step(existing_user, onboarding_status)
            if onboarding_status == 8:
                return Response(
                    {
                        'message': f'{email} Already Exists,please login',
                        "user_id":str(user_id),
                        "onboarding_status":onboarding_step}, 
                        status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(
                    {
                        'message': 'Please login and complete the on-boarding process',
                        "user_id":str(user_id),
                        "redirect_step":redirect_step,
                        "onboarding_status":onboarding_step}, 
                        status=status.HTTP_200_OK)
            
    
    def delete(self,request,id):
        try:
            collections=[resume_data,userLogin_Details,dashboard_data,billing_details,nudges,nudge_preference,payments_collection,subscriptions_collection]
            obj = users_registration.find_one({"_id": ObjectId(id)})
            if obj:
                users_registration.delete_one({"_id": ObjectId(id)})
                for collection in collections:
                    col = collection.find_one({"user_id":str(id)})
                    if col:
                        collection.delete_one({"user_id":str(id)})
                return Response({"message": "Your account has been successfully deleted"}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "No result found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error":str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class logout_api(APIView):
    def post(self, request):

        request_body=request.body
        body=json.loads(request_body)
        user_id =body["user_id"]
        
        # Check if the user exists in your database (pymongo).
        user = users_registration.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            return Response({"message": "No User found"}, status=status.HTTP_400_BAD_REQUEST)

        userLogin_Details.delete_one({"user_id":str(user_id)})
        return Response({"message": "Successfully logged out", "user_id":user_id}, status=status.HTTP_200_OK)


# first time send OTP for Update Phone Number
class Update_Phone_Number_View(APIView):
    def post(self, request):
        try:
            request_body=request.body
            body=json.loads(request_body)
            user_id=body["user_id"]
            country_code=body["country_code"]
            phone_number=body["phone_number"]
            number_data = users_registration.find_one({'_id': ObjectId(user_id)})
            if "phone_number" in number_data:
                if number_data["phone_number"]==phone_number:
                    return Response({"message" :"New Number is same as existing Number."}, status = status.HTTP_400_BAD_REQUEST)
        
            if users_registration.find_one({"phone_number": phone_number, "_id": {"$ne": user_id}}):
                return Response({"message" :"This Number already exists!."}, status = status.HTTP_400_BAD_REQUEST)
    
            else:       
                otp = generate_otp(6)
                redis_client_update_number.setex(f'{user_id}_otp', 300, otp)
                redis_client_update_number.setex(f'{user_id}_number', 300, phone_number)

                message = settings.client.messages.create(
            body=f''' Your youe verification code is: {otp} 
            The code expires in 5 minutes.''',
            from_=settings.TWILIO_NUMBER,
            to=f"{country_code}{phone_number}",
            #to=Mobile_number
        )
                return Response({"message": "otp send sucessfully","phone_number":phone_number,"country_code":country_code,"user_id":user_id}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": "An error occurred","error":str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)     


#Resend OTP if OTP expire for Update Phone Number
class Resend_OTP_Phone_Number_View(APIView):
    def post(self,request):
        try:
            request_body=request.body
            body=json.loads(request_body)
            user_id=body["user_id"]
            country_code=body["country_code"]
            phone_number=body["phone_number"]
            otp = generate_otp(6)
            redis_client_update_number.setex(f'{user_id}_otp', 300, otp)
            redis_client_update_number.setex(f'{user_id}_number', 300, phone_number)

            message = settings.client.messages.create(
            body=f''' Your youe verification code is: {otp} 
            The code expires in 5 minutes.''',
            from_=settings.TWILIO_NUMBER,
            to=f"{country_code}{phone_number}",
            #to=Mobile_number
        )
            
            return Response({"message": "OTP Generated","phone_number":phone_number,"country_code":country_code,"user_id":user_id})
        except Exception as e:
            return Response({"message": "An error occurred","error":str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#verify otp for update phonr number
class Phone_Number_VerifyOTP_View(generics.GenericAPIView):
    def post(self, request):
        try:
            request_body=request.body
            body=json.loads(request_body)
            user_id=body["user_id"]
            otp_data=body["otp"]
            country_code=body["country_code"]
            phone_number=body["phone_number"]

            otp = otp_data.encode('utf-8')
            number = phone_number.encode('utf-8')
            otp_code = redis_client_update_number.get(f'{user_id}_otp')
            redies_number = redis_client_update_number.get(f'{user_id}_number')
            message = "Code is invalid"
            if (number!=redies_number) and (otp_code!=otp):
                return Response({"status": "Your OTP has expired. Please resend new one to continue."},status=status.HTTP_400_BAD_REQUEST)
            if (number==redies_number) and (otp_code!=otp):
                return Response({"status": "fail", "message": message},status=status.HTTP_400_BAD_REQUEST)
            if (number!=redies_number) and (otp_code==otp):
                return Response ({"status": "fail", "message": f"No user with email  found"},status=status.HTTP_400_BAD_REQUEST)
        
            data = {
                "country_code":country_code,
                "phone_number":phone_number,
                "updated_at":datetime.datetime.now()
                

            }
        
 
        # Update Phone Number field
            users_registration.update_one({'_id': ObjectId(user_id)}, {'$set':  data})
            redis_client_update_number.delete(f'{user_id}_otp')
            redis_client_update_number.delete(f'{user_id}_number')
            return Response({"message": "otp verified sucessfully","user_id":user_id}, status=status.HTTP_200_OK)     
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#Register email send otp, email update
class register_email_View(APIView):

    def post(self, request):
      try:
        request_body=request.body
        body=json.loads(request_body)
        email=body["email"]
        
        existing_user=users_registration.find_one({"email": email})
        if existing_user:
            
            onboarding_process = existing_user.get("onboarding_process", {})
            if onboarding_process is None:
                return Response({"message": "Onboarding process information not found"}, status=status.HTTP_400_BAD_REQUEST)

            onboarding_status = onboarding_process.get("step")
            onboarding_step= onboarding_status_fun(onboarding_status)
            redirect_step = calculate_redirect_step(existing_user, onboarding_status)
            if onboarding_status == 8:
                return Response(
                    {
                        'message': f'{email} already exists, please login',
                        "user_id":str(existing_user["_id"]),
                        "onboarding_status":onboarding_step}, 
                        status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(
                    {
                        'message': 'Please login and complete the onboarding process',
                        "user_id":str(existing_user["_id"]),
                        "redirect_step":redirect_step,
                        "onboarding_status":onboarding_step}, 
                        status=status.HTTP_200_OK)
        
        else:
            
            otp = generate_otp(6)
            redis_client.setex(f'{email}_otp', 300, otp)
            redis_client.setex(f'{email}_email', 300, email)
            subject = "youe – Email Verification Email"
            html = "users/emailTemplate.html"
            mydict = {"otp": otp}
            send_template_emails(subject,email,html,mydict)
            return Response({"message": "Successfully OTP Sent", "email":email}, status=status.HTTP_200_OK)
      except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#register verify otp
class register_verifyotp(APIView):
    def post(self, request):
        try:
            request_body=request.body
            body=json.loads(request_body)
            email_data = body["email"]
            otp_data = body["otp"]
    
            otp = otp_data.encode('utf-8')
            email = email_data.encode('utf-8')
            otp_code = redis_client.get(f'{email_data}_otp')
            email1 = redis_client.get(f'{email_data}_email')
            message = "Code is invalid"

            if (email!=email1) and (otp_code!=otp):
                return Response({"status": "Your OTP has expired. Please resend new one to continue."},status=status.HTTP_400_BAD_REQUEST)
            if (email==email1) and (otp_code!=otp):
               return Response({"status": "fail", "message": message},status=status.HTTP_400_BAD_REQUEST)
            if (email!=email1) and (otp_code==otp):
                return Response ({"status": "fail", "message": f"No user with email  found"},status=status.HTTP_400_BAD_REQUEST)
        
        
            redis_client.delete(f'{email_data}_otp')
            redis_client.delete(f'{email_data}_email')
           
            return Response({'otp_verified': "OTP Verified","email":email_data},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#This API we can use for registered email resend otp
class Generate_OTP_Email_VIew(APIView):
    def post(self,request):
        try:
            request_body=request.body
            body=json.loads(request_body)
            email= body["email"]
            otp = generate_otp(6)
            redis_client.setex(f'{email}_otp', 300, otp)
            redis_client.setex(f'{email}_email', 300, email)

            subject = "youe – Email Verification Email"
            html = "users/emailTemplate.html"
            mydict = {"otp": otp}
            send_template_emails(subject,email,html,mydict)
            return Response({"message": "OTP Generated","email":email})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#Update email for first time send OTP
class Update_email_View(APIView):

    def post(self, request):
        
        try:
            request_body=request.body
            body=json.loads(request_body)
            user_id=body["user_id"]
            email=body["email"]
            email_data = users_registration.find_one({'_id': ObjectId(user_id)})
            if email_data["email"]==email:
                return Response({"message" :"New email is same as existing email."}, status = status.HTTP_400_BAD_REQUEST)
        
            if users_registration.find_one({"email": email, "_id": {"$ne": user_id}}):
                return Response({"message" :"This email already exists!."}, status = status.HTTP_400_BAD_REQUEST)
    
            else:
            
                otp = generate_otp(6)
                redis_client_update_email.setex(f'{user_id}_otp', 300, otp)
                redis_client_update_email.setex(f'{user_id}_email', 300, email)
                subject = "youe – Update Email Verification Email"
                content = f'''Dear User,<br><br>

                To Update Your Email, please use the following One-Time Password (OTP):<b> {otp}</b><br><br>


                Please enter this OTP on the verification page or provide it when prompted. 
                The OTP is valid for 5 minutes for security purposes. If the OTP expires, 
                you may request a new one by visiting the verification page again.<br><br><br>

                Regards,<br>
                Team – youe'''

                send_emails(subject, email, content)
            
                return Response({"message": "Successfully OTP Sent", "email":email,"user_id":user_id}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    


#Verify OTP for Update new Mail
class Update_Email_VerifyOTP(APIView):
   

    def post(self, request):
        try:
            request_body=request.body
            body=json.loads(request_body)
            email_data = body["email"]
            otp_data = body["otp"]
            user_id=body["user_id"]

            otp = otp_data.encode('utf-8')
            email = email_data.encode('utf-8')
            otp_code = redis_client_update_email.get(f'{user_id}_otp')
            email1 = redis_client_update_email.get(f'{user_id}_email')
            message = "Code is invalid"

            if (email!=email1) and (otp_code!=otp):
                return Response({"status": "Your OTP has expired. Please resend new one to continue."},status=status.HTTP_400_BAD_REQUEST)
            if (email==email1) and (otp_code!=otp):
               return Response({"status": "fail", "message": message},status=status.HTTP_400_BAD_REQUEST)
            if (email!=email1) and (otp_code==otp):
                return Response ({"status": "fail", "message": f"No user with email  found"},status=status.HTTP_400_BAD_REQUEST)
        
            data={"email":email_data,
              "updated_at":datetime.datetime.now()}
            users_registration.update_one({'_id': ObjectId(user_id)}, {'$set':  data})
        
            redis_client_update_email.delete(f'{user_id}_otp')
            redis_client_update_email.delete(f'{user_id}_email')
            return Response({'otp_verified': "OTP Verified","message":"email updated sucessfully","email":email_data},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#Resend OTP for Update Email
class Generate_OTP_Update_Email_View(APIView):
    def post(self,request):
        try:
            request_body=request.body
            body=json.loads(request_body)
            email= body["email"]
            user_id= body["user_id"]
            otp = generate_otp(6)
            redis_client_update_email.setex(f'{user_id}_otp', 300, otp)
            redis_client_update_email.setex(f'{user_id}_email', 300, email)

            subject = "youe – Update Email Verification Email"
            content = f'''Dear User,<br><br>

                            To Update Your Email, please use the following One-Time Password (OTP):<b> {otp}</b><br><br>


                            Please enter this OTP on the verification page or provide it when prompted. 
                            The OTP is valid for 5 minutes for security purposes. If the OTP expires, 
                            you may request a new one by visiting the verification page again.<br><br><br>

                            Regards,<br>
                            Team – youe'''

            send_emails(subject, email, content)
            return Response({"message": "OTP Generated","email":email,"user_id":user_id})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#First time send OTP for Update Password
class Password_Update_View(APIView):
    def post(self, request):
        try:
            request_body=request.body
            body=json.loads(request_body)
            user_id=body["user_id"]
            user_data=users_registration.find_one({"_id":ObjectId(user_id)})
            email=user_data["email"]
            otp = generate_otp(6)
            redis_client_update_password.setex(f'{user_id}_otp', 300, otp)
            redis_client_update_password.setex(f'{user_id}_email', 300, email)
            subject = "youe – Update Password Verification Email"
            content = f'''Dear User,<br><br>

                To Update Password, please use the following One-Time Password (OTP):<b> {otp}</b><br><br>


                Please enter this OTP on the verification page or provide it when prompted. 
                The OTP is valid for 5 minutes for security purposes. If the OTP expires, 
                you may request a new one by visiting the verification page again.<br><br><br>

                Regards,<br>
                Team – youe'''

            send_emails(subject, email, content)
            return Response({"message": "Successfully OTP Sent","user_id":user_id})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
'''verify OTP`for update password'''
class Update_Password_VerifyOTP(APIView):

    def post(self, request):
        try:
            request_body=request.body
            body=json.loads(request_body)
            password = body["password"]
            password_encrypt=hash_password(password)
            otp_data = body["otp"]
            user_id=body["user_id"]
            user_data=users_registration.find_one({"_id":ObjectId(user_id)})
            email_data=user_data["email"]

            otp = otp_data.encode('utf-8')
            email = email_data.encode('utf-8')
            otp_code = redis_client_update_password.get(f'{user_id}_otp')
            email1 = redis_client_update_password.get(f'{user_id}_email')
            message = "Code is invalid"

            if (email!=email1) and (otp_code!=otp):
                return Response({"status": "Your OTP has expired. Please resend new one to continue."},status=status.HTTP_400_BAD_REQUEST)
            if (email==email1) and (otp_code!=otp):
               return Response({"status": "fail", "message": message},status=status.HTTP_400_BAD_REQUEST)
            if (email!=email1) and (otp_code==otp):
                return Response ({"status": "fail", "message": f"No user with email  found"},status=status.HTTP_400_BAD_REQUEST)
        
            data={"password":password_encrypt,
              "updated_at":datetime.datetime.now()}
            users_registration.update_one({'_id': ObjectId(user_id)}, {'$set':  data})
        
            redis_client_update_password.delete(f'{user_id}_otp')
            redis_client_update_password.delete(f'{user_id}_email')
            return Response({'otp_verified': "OTP Verified","message":"password  updated sucessfully","user_id":user_id},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

"""generate otp for update password"""
class Generate_OTP_Update_Password_VIew(APIView):
    def post(self,request):
        try:
            request_body=request.body
            body=json.loads(request_body)
            user_id=body["user_id"]
            user_data=users_registration.find_one({"_id":ObjectId(user_id)})
            email=user_data["email"]
            otp = generate_otp(6)
            redis_client_update_password.setex(f'{user_id}_otp', 300, otp)
            redis_client_update_password.setex(f'{user_id}_email', 300, email)

            subject = "youe – Update Password Verification Email"
            content = f'''Dear User,<br><br>

                            To update password, please use the following One-Time Password (OTP):<b> {otp}</b><br><br>


                            Please enter this OTP on the verification page or provide it when prompted. 
                            The OTP is valid for 5 minutes for security purposes. If the OTP expires, 
                            you may request a new one by visiting the verification page again.<br><br><br>

                            Regards,<br>
                            Team – youe'''

            send_emails(subject, email, content)
            return Response({"message": "OTP Generated","user_id":user_id})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#update two fact True or False
class Update_Two_FactAuth_View(APIView):
    def post(self, request):
        try:
            request_body=request.body
            body=json.loads(request_body)
            user_id = body["user_id"]
            two_fact_auth=body["2fa"]
            data={"2fa":two_fact_auth,
              "updated_at":datetime.datetime.now()}
            users_registration.update_one({'_id': ObjectId(user_id)}, {'$set':  data})

            return Response({"message": "Successfully Updated"})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class userLogin(APIView):

    def post(self,request):
        email=request.data.get('email')
        password=request.data.get('password')
        user_data1 = users_registration.find_one({"email": email})
        

        if user_data1 is None:
            return Response({"message":"Email doesn't exist","onboarding_status":0}, status=status.HTTP_401_UNAUTHORIZED)
        user_object_id = user_data1["_id"]
        signup_type = user_data1.get("signup_type", "")

        if "password" not in user_data1:
            return Response({"message": "You have signed up with LinkedIn. Please use the LinkedIn sign-in option."}, status=status.HTTP_400_BAD_REQUEST)
        two_fact=user_data1["2fa"]
        onboarding_status=user_data1["onboarding_process"]["step"]
        onboarding_step= onboarding_status_fun(onboarding_status)

        
        if two_fact==True:

            hashed_password = user_data1["password"]
            if check_password(password, hashed_password):
                redirect_step = calculate_redirect_step(user_data1, onboarding_status)

                if onboarding_status!=8:
                    return Response(
                        {"message": "Please complete the onboarding process",
                        "user_id":str(user_object_id),
                        "onboarding_status":onboarding_step,
                        "redirect_step":redirect_step}, 
                        status=status.HTTP_200_OK)
                
                else:

                
                    otp = generate_otp(6)
                    redis_client_update_2FA.setex(f'{email}_otp', 300, otp)
                    redis_client_update_2FA.setex(f'{email}_email', 300, email)
                    subject = "youe – Login Verification Email"
                    content = f'''Dear User,<br><br>

                    To Login your Account, please use the following One-Time Password (OTP):<b> {otp}</b><br><br>


                    Please enter this OTP on the verification page or provide it when prompted. 
                    The OTP is valid for 5 minutes for security purposes. If the OTP expires, 
                    you may request a new one by visiting the verification page again.<br><br><br>

                    Regards,<br>
                    Team – youe'''

                    send_emails(subject, email, content)
                    return Response({"two_fact_auth":two_fact, "message": "OTP sent successfully","email":email,"onboarding_status":onboarding_step,"onboarding_step":onboarding_status,"user_id":str(user_object_id)},status=status.HTTP_200_OK)
                
            else:
            # Password is incorrect
                    return Response({"message":"incorrect password, please try again","onboarding_status":onboarding_step,"user_id":str(user_object_id)}, status=status.HTTP_401_UNAUTHORIZED)
          
        else:
          user_data = users_registration.find_one({"email": email})
          if user_data is None:
            return Response({"message":"Email doesn't exist","onboarding_status":0}, status=status.HTTP_401_UNAUTHORIZED)
          hashed_password = user_data1["password"]
          if check_password(password, hashed_password):
            redirect_step = calculate_redirect_step(user_data1, onboarding_status)
            
            
            if onboarding_status!=8:
                return Response(
                    {"message": "Please complete the onboarding process",
                    "onboarding_status":onboarding_step,
                    "redirect_step":redirect_step,
                    "user_id":str(user_object_id)}, 
                    status=status.HTTP_200_OK)
            else:
                user_object_id = user_data["_id"]
                user_subscriptions = subscriptions_collection.find_one({"user_id": str(user_object_id)})
                expiry_datetime = datetime.datetime.now() + datetime.timedelta(minutes=25)
                session_token = secrets.token_urlsafe(32)
                response_data = {
                    "message": "successfully logged in",
                    "onboarding_status": onboarding_step,
                    "user_id": str(user_object_id),
                    "two_fact_auth": two_fact
                }
                if user_subscriptions:
                    response_data["subscription_status"] = user_subscriptions.get("status")
    
                # Create the response with the updated data
                response = Response(response_data, status=status.HTTP_200_OK)
                response.set_cookie(key='session_token', value=session_token, expires=expiry_datetime, httponly=True)

                
                session_data = {
                    "session_key": session_token,  # Store session_key 
                    "user_id": str(user_object_id),
                    "expiry_datetime":expiry_datetime
                }
                # Insert session data into userLogin_Details collection
                session_key = userLogin_Details.insert_one(session_data).inserted_id
                users_registration.update_one({'_id': ObjectId(user_object_id)}, {'$set': {'last_login': datetime.datetime.now()}})
                return response
          else:
                # Password is incorrect
                return Response({"message":"incorrect password, please try again","onboarding_status":onboarding_step,"user_id":str(user_object_id)}, status=status.HTTP_401_UNAUTHORIZED)

    def get(self, request):
            session_token = request.COOKIES.get('session_token')
            print(session_token)
            if session_token:
                session_data = userLogin_Details.find_one({"session_key": session_token})
                
                if session_data is not None:
                    id=session_data["_id"]
                    expiry_datetime = session_data["expiry_datetime"]
                
                    if expiry_datetime < datetime.datetime.now():
                        # Session has expired, perform automatic logout
                        userLogin_Details.delete_one({"_id":id})
                        return Response({'message': 'Session expired, you have been logged out.'}, status=status.HTTP_200_OK)
                    else:
                        return Response({'message': 'Session active.'}, status=status.HTTP_200_OK)
                else:
                    return Response({'message': 'session key not found.'}, status=status.HTTP_401_UNAUTHORIZED)
            else:
                return Response({'message': 'No session key found.'}, status=status.HTTP_401_UNAUTHORIZED)


class VerifyOTP_twofactorauth(generics.GenericAPIView):
    # serializer_class = VerifySerializer
    # queryset = Register.objects.all()


    def post(self, request, format=None):
        email_data = request.data.get('email')
        otp_data = request.data.get('otp')

        otp = otp_data.encode('utf-8')
        email = email_data.encode('utf-8')
        otp_code = redis_client_update_2FA.get(f'{email_data}_otp')
        email1 = redis_client_update_2FA.get(f'{email_data}_email')
        message = "Code is invalid"
        user_data = users_registration.find_one({"email": email_data})
        user_object_id = user_data["_id"]
        if (email!=email1) and (otp_code!=otp):
            return Response({"status": "Your OTP has expired. Please resend new one to continue."},status=status.HTTP_400_BAD_REQUEST)
        if (email==email1) and (otp_code!=otp):
           return Response({"status": "fail", "message": message},status=status.HTTP_400_BAD_REQUEST)
        if (email!=email1) and (otp_code==otp):
            return Response ({"status": "fail", "message": f"No user with email  found"},status=status.HTTP_400_BAD_REQUEST)
        
        # redis_client.delete(f'{email_data}_otp')
        # redis_client.delete(f'{email_data}_email')

        profile = users_registration.find_one({"_id": ObjectId(user_object_id)})
        session_token = secrets.token_urlsafe(32)
        expiry_datetime = datetime.datetime.now() + datetime.timedelta(minutes=5)
    
        response = Response({"message": "OTP Verified","user_id":str(user_object_id)}, status=status.HTTP_200_OK)     
        user_object_id = user_data["_id"]
        user_subscriptions = subscriptions_collection.find_one({"user_id": str(user_object_id)})   
        response.set_cookie(key='session_token', value=session_token, httponly=True)

            
        session_data = {
                    "session_key": session_token,  # Store session_key 
                    "user_id": str(user_object_id),
                    "expiry_datetime":expiry_datetime
                }
            # Insert session data into userLogin_Details collection
        session_key = userLogin_Details.insert_one(session_data).inserted_id
        redis_client_update_2FA.delete(f'{email_data}_otp')
        redis_client_update_2FA.delete(f'{email_data}_email')
        return response
        
    '''Get Session'''   
    def get(self, request):
            session_token = request.COOKIES.get('session_token')
            print(session_token)
            if session_token:
                session_data = userLogin_Details.find_one({"session_key": session_token})
                
                if session_data is not None:
                    id=session_data["_id"]
                    expiry_datetime = session_data["expiry_datetime"]
                
                    if expiry_datetime < datetime.datetime.now():
                        # Session has expired, perform automatic logout
                        userLogin_Details.delete_one({"_id":id})
                        return Response({'message': 'Session expired, you have been logged out.'}, status=status.HTTP_200_OK)
                    else:
                        return Response({'message': 'Session active.'}, status=status.HTTP_200_OK)
                else:
                    return Response({'message': 'session key not found.'}, status=status.HTTP_401_UNAUTHORIZED)
            else:
                return Response({'message': 'No session key found.'}, status=status.HTTP_401_UNAUTHORIZED)



#resend OTP for 2FA
class Generate_OTP_2FA_VIew(APIView):
    def post(self,request):
        try:
            request_body=request.body
            body=json.loads(request_body)
            email= body["email"]
            otp = generate_otp(6)
            redis_client_update_2FA.setex(f'{email}_otp', 300, otp)
            redis_client_update_2FA.setex(f'{email}_email', 300, email)

            subject = "youe – Login Verification Email"
            content = f'''Dear User,<br><br>

                            To Login Your Account, please use the following One-Time Password (OTP):<b> {otp}</b><br><br>


                            Please enter this OTP on the verification page or provide it when prompted. 
                            The OTP is valid for 5 minutes for security purposes. If the OTP expires, 
                            you may request a new one by visiting the verification page again.<br><br><br>

                            Regards,<br>
                            Team – youe'''

            send_emails(subject, email, content)
            return Response({"message": "OTP Generated","email":email})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProfileImageUploadView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            data=request.data
            id=request.data.get("user_id")
            ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg'}
            user_image=request.FILES['image']
            extension = os.path.splitext(user_image.name)[-1]
            if extension in ALLOWED_EXTENSIONS:
                s3_storage = S3Boto3Storage()
                file_path =f'image/{id}{extension}'
                saved_file_path = s3_storage.save(file_path, ContentFile(user_image.read()))
                print(saved_file_path)
              
                file_url = s3_storage.url(saved_file_path)
                print(file_url)
                data = {
                "profile_image":file_url,
                "updated_at":datetime.datetime.now(),
                }
                users_registration.update_one({'_id': ObjectId(id)}, {'$set':  data})
                return Response({"message": "Image uploaded Sucessfully"}, status=status.HTTP_200_OK)
            return Response({"message": "Not a image please upload a image"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ProfileImageDeleteView(APIView):
    def delete(self, request,id):
        try:
            user_data=users_registration.find_one({'_id': ObjectId(id)})
            if "profile_image" in user_data:
                profile_image=user_data["profile_image"]
                url_path = urlsplit(profile_image).path
                s3_storage = S3Boto3Storage()
                s3_storage.delete(url_path)
                users_registration.update_one({'_id': ObjectId(id)}, {'$unset': {'profile_image': 1}})
                return Response({"message": "Image deleted Sucessfully"}, status=status.HTTP_200_OK)
            return Response({"message": "Your image has already deleted"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
'''Create Profile'''
class Profile_Register(APIView):

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
      
    def validate_name(self,name):
        # Regular expression to check if the name contains only alphabetic characters
        return bool(re.match("^[a-zA-Z]*$", name))

    def validate_phone_number(self,phone_number):
        # Regular expression to check if the name contains only alphabetic characters
        return bool(re.match("^[0-9]*$", phone_number))

    def validate_country_code(self,country_code):
        # Regular expression to check if the name contains only alphabetic characters
        return bool(re.match("^\+\d+$", country_code))
         
    # def validate_phone_number(self, phone_number,country_code):
    #     try:
    #         parsed_number = phonenumbers.parse(phone_number,None)
    #         return phonenumbers.is_valid_number(parsed_number)
    #     except phonenumbers.phonenumberutil.NumberParseException:
    #         return False
    
    def post(self,request):
        try:
            request_data=request.body
            body=json.loads(request_data)

            mandatory_fields = {
                'first_name': "First Name is mandatory",
                'last_name': "Last Name is mandatory",
                'birth_year': "Birth Year is mandatory",
                'country_code': "Country Code is mandatory",
                'phone_number': "Phone Number is mandatory"
            }

            # Check each mandatory field and return error response if missing
            for field, error_message in mandatory_fields.items():
                if not body.get(field):
                    return Response({"message": error_message}, status=status.HTTP_400_BAD_REQUEST)


            user_id=body['user_id']

            first_name=body['first_name']
            last_name=body['last_name']
            if not (len(first_name)>=1 and len(first_name)<=35):
                return Response({"message": "First Name must be between 1 and 35 characters"}, status=status.HTTP_400_BAD_REQUEST)
            if not (len(last_name)>=1 and len(last_name)<=35):
                return Response({"message": "Last Name must be between 1 and 35 characters"}, status=status.HTTP_400_BAD_REQUEST)
            if not self.validate_name(first_name):
                return Response({"message": "First Name can only contain alphabetic characters"}, status=status.HTTP_400_BAD_REQUEST)
            if not self.validate_name(last_name):
                return Response({"message": "Last Name can only contain alphabetic characters"}, status=status.HTTP_400_BAD_REQUEST)

            gender=body['gender']

            birth_year=body['birth_year']
            current_year = datetime.datetime.now().year
            if not (current_year - birth_year >= 18 and current_year - birth_year <= 65):
                return Response({"message": "Birth Year must be between 18 and 65"}, status=status.HTTP_400_BAD_REQUEST)


            country_code=body['country_code']
            if not (len(country_code)>=2 and len(country_code)<=4):
                return Response({"message": "Invalid country code"}, status=status.HTTP_400_BAD_REQUEST)
            if not self.validate_country_code(country_code):
                return Response({"message": "Country Code can only contain numeric characters"}, status=status.HTTP_400_BAD_REQUEST)
            
            
            phone_number=body['phone_number']
            if not (len(phone_number)>=5 and len(phone_number)<=15):
                return Response({"message": "Invalid phone number "}, status=status.HTTP_400_BAD_REQUEST)
            if not self.validate_phone_number(phone_number):
                return Response({"message": "phone_number can only contain numeric characters"}, status=status.HTTP_400_BAD_REQUEST)

            # full_phone_number = country_code + phone_number
            # # print("full_phone_number",full_phone_number)
            # if not self.validate_phone_number(full_phone_number,country_code):
            #     return Response({"message": "Invalid Phone Number for the given country code"}, status=status.HTTP_400_BAD_REQUEST)
            
            
            # Retrieve the profile document
            user = users_registration.find_one({"_id":ObjectId(user_id)})
            if not user:
                return Response({"message": "User not found"}, status=status.HTTP_400_BAD_REQUEST)
            signup_type = user.get('signup_type',())
            signup = singup_type_func(signup_type)

            body.pop("user_id")
            user_ip = self.get_client_ip(request)

            user_data = {
                "first_name": first_name,
                "last_name": last_name,
                "gender": gender,
                "birth_year":birth_year,
                "country_code":country_code,
                "phone_number":phone_number,
                "updated_at": datetime.datetime.now(),
                "ip_address": user_ip,
                "profile_image":"",
                
                "communication_preferences":{
                    "account_notifications":True,
                    "product_updates":True,
                    "newsletter":True 
                    },
                "account_integrations":{
                    "linkedin":signup
                    }
            }

            
            users_registration.update_one({'_id': ObjectId(user_id)}, {'$set': {**user_data, "onboarding_process": {"step": 1, "process": "setup profile"}}})
            return Response({"message": "Successfully Updated","user_id":user_id})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


'''Questionnaire Screen 1'''
class Questionnaire(APIView):
    def get(self, request, pk):
        try:
            # Retrieve the profile document
            profile = users_registration.find_one({'_id': ObjectId(pk)})
            if profile:
                user_id=profile["_id"]
                questionnaire = profile.get('questionnaire', {})
                if questionnaire:
                    extracted_data = {
                        "satisfaction_with_current_role": questionnaire.get("satisfaction_with_current_role"),
                        "confidence_about_next_career_runway": questionnaire.get("confidence_about_next_career_runway"),
                        "hoping_to_get_out_of_youe": questionnaire.get("hoping_to_get_out_of_youe")
                    }
                    return Response({"user_id":str(user_id),"questionnaire": extracted_data})
                else:
                    return Response({"message": "Questionnaire not available"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"message": "No data found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self,request):
        try:
            request_data=request.body
            data=json.loads(request_data)
            pk=data['user_id']
            profile = users_registration.find_one({'_id': ObjectId(pk)})
            if not profile:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
            questionnaire=profile.get("questionnaire",{})
            onboarding_process = profile.get("onboarding_process", {})
            onboarding_status = onboarding_process.get("step", 0)
            
            data.pop("user_id")

            fields_to_check = ["satisfaction_with_current_role"]
            if data:
                if any(key not in questionnaire for key in fields_to_check):
                    users_registration.update_one({'_id': ObjectId(pk)}, 
                                        [
                                    {
                                        "$addFields": {
                                        "updated_at": datetime.datetime.now(),
                                        "onboarding_process":{"step":2,"process":"Questionnaire 1"},
                                        "questionnaire": { 
                                            "$mergeObjects": [ 
                                            "$$ROOT.questionnaire",data
                                    
                                            ]
                                        }
                                        }
                                    }
                                    ],
                                    upsert=True)
                    return Response({"message": "Successfully Updated","user_id":pk})
                else:
                    users_registration.update_one({'_id': ObjectId(pk)}, 
                                        [
                                    {
                                        "$addFields": {
                                        "updated_at": profile["updated_at"],
                                        "questionnaire": { #overwrite questionnaire field
                                            "$mergeObjects": [ #Merging the object to Root
                                            "$$ROOT.questionnaire",data #$$ROOT refers to current object.Query["$$ROOT.serviceDetails",updateObject]
                                    
                                            ]
                                        }
                                        }
                                    }
                                    ],
                                    upsert=True)
                    return Response({"message": "Successfully Updated","user_id":pk})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


'''Questionnaire Screen 2'''
class Questionnaire_2(APIView):
    def get(self, request, pk):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            user = users_registration.find_one({'_id': ObjectId(pk)})
            sorted_experience=""
            if user:
                user_id=user["_id"]
                questionnaire_data=user.get("questionnaire",{})
                print(questionnaire_data)
                experience = profile.get('experience', {})
                if experience:

                    def get_end_date(experience_record):
                        end_date = experience_record.get("end_date",)
                        current=datetime.datetime.now()
                        if end_date is None:
                            return datetime.datetime(1900, 1, 1)  
                        if end_date == "Present":
                            return current
                        return datetime.datetime.strptime(end_date, "%B %Y")
                        # Handle additional checks if needed for other null values

                    
                    sorted_experience = sorted(experience, key=get_end_date, reverse=True)
                
                fields_to_check = ["career_runway_role_description"]
                if any(key  in questionnaire_data for key in fields_to_check):
                    runway=questionnaire_data.get("career_runway_role_description",{})
                    extracted_data = {
                                "sector": runway.get("sector", ""),
                                "function": runway.get("function", ""),
                                "role": runway.get("role", ""),
                                "company_type": runway.get("company_type", ""),
                                "domain":runway.get("domain", ""),
                                "rank": runway.get("rank", ""),
                                }
                    
                    return Response({"user_id":str(user_id),"questionnaire": extracted_data})
                
            
                if sorted_experience:
                    current_experience = sorted_experience[0]  # Get the latest experience
                    role= current_experience.get("role", "")
                   
                    extracted_data = {
                        "sector": "",
                        "function": "",
                        "company_type":"",
                        "rank": "",
                        "role": role,
                        "domain":""
                    }
                    return Response({"user_id":str(user_id),"questionnaire": extracted_data})
                else:
                    return Response({"message": "experience not available"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"message": "No data found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self,request):
        try:
            request_data=request.body
            data=json.loads(request_data)
            pk=data['user_id']
            profile = users_registration.find_one({'_id': ObjectId(pk)})
            if not profile:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
            questionnaire=profile.get("questionnaire",{})
            onboarding_process = profile.get("onboarding_process", {})
            onboarding_status = onboarding_process.get("step", 0)
            
            data.pop("user_id")
            fields_to_check = ["career_runway_role_description"]
            if data:
                if any(key not in questionnaire for key in fields_to_check):
                    users_registration.update_one({'_id': ObjectId(pk)}, 
                                        [
                                    {
                                        "$addFields": {
                                        "updated_at": datetime.datetime.now(),
                                        "onboarding_process":{"step":4,"process":"Questionnaire 2"},
                                        "questionnaire": { #overwrite questionnaire field
                                            "$mergeObjects": [ #Merging the object to Root
                                            "$$ROOT.questionnaire",data #$$ROOT refers to current object.Query["$$ROOT.serviceDetails",updateObject]
                                    
                                            ]
                                        }
                                        }
                                    }
                                    ],
                                    upsert=True)
                    return Response({"message": "Successfully Updated","user_id":pk})
                else:
                    users_registration.update_one({'_id': ObjectId(pk)}, 
                                        [
                                    {
                                        "$addFields": {
                                        "updated_at": datetime.datetime.now(),
                                        "questionnaire": { #overwrite questionnaire field
                                            "$mergeObjects": [ #Merging the object to Root
                                            "$$ROOT.questionnaire",data #$$ROOT refers to current object.Query["$$ROOT.serviceDetails",updateObject]
                                    
                                            ]
                                        }
                                        }
                                    }
                                    ],
                                    upsert=True)
                    return Response({"message": "Successfully Updated","user_id":pk})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

'''Questionnaire Screen 3'''
class Questionnaire_3(APIView):
    def get(self, request, pk):
        try:
            # Retrieve the profile document
            profile = users_registration.find_one({'_id': ObjectId(pk)})
            if profile:
                user_id=profile["_id"]
                questionnaire = profile.get('questionnaire', {})
                if questionnaire:
                    extracted_data = {
                        "clear_vision_for_next_career_runway": questionnaire.get("clear_vision_for_next_career_runway"),
                        "role_at_end_of_career_runway": questionnaire.get("role_at_end_of_career_runway"),
                        "current_career_choice": questionnaire.get("current_career_choice"),
                        "career_stream_of_interest": questionnaire.get("career_stream_of_interest"),
                        "career_runway_duration": questionnaire.get("career_runway_duration"),

                    }
                    return Response({"user_id":str(user_id),"questionnaire": extracted_data})
                else:
                    return Response({"message": "Questionnaire not available"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"message": "No data found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occured","error" :str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self,request):
        try:
            request_data=request.body
            data=json.loads(request_data)
            print(data)
            clear_vision = data["clear_vision_for_next_career_runway"]
            pk=data['user_id']
            profile = users_registration.find_one({'_id': ObjectId(pk)})
            resume_details = resume_data.find_one({'user_id': pk})
            cost_data = Cost_Details.find_one({'user_id': pk})
            if not profile:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
            questionnaire=profile.get("questionnaire",{})
            onboarding_process = profile.get("onboarding_process", {})
            onboarding_status = onboarding_process.get("step", 0)
            
            data.pop("user_id")
            fields_to_check = ["clear_vision_for_next_career_runway"]
            if data:
                if any(key not in questionnaire for key in fields_to_check):
                    
                    timeline = data["career_runway_duration"]
                    clear_vision=data["clear_vision_for_next_career_runway"]
                    current_role = questionnaire["career_runway_role_description"]
                    industry = current_role["sector"]
                    seniority= current_role["rank"]
                    role = current_role["role"]
                    company_type = current_role["company_type"]
                    function = current_role["function"]
                    domain = current_role["domain"]
                    work_experience = resume_details["experience"]
                    certifications = resume_details["certifications_and_courses"]
                    if clear_vision== False:
                        users_registration.update_one({'_id': ObjectId(pk)}, {'$set': {
                                        "questionnaire.initiated_steps_towards_next_goal": "",
                                        "questionnaire.list_significant_actions_taken": []
                                    }})
                    if timeline < 24:
                     
                     try: 
                        timeline = int(timeline * 30)
                        users_registration.update_one({'_id': ObjectId(pk)},{'$set': {"questionnaire.consider_intermediate_role": ""}})
                        if (data["clear_vision_for_next_career_runway"] == True):
                            users_registration.update_one({'_id': ObjectId(pk)}, 
                                        [
                                    {
                                        "$addFields": {
                                        "updated_at": datetime.datetime.now(),   
                                        "onboarding_process":{"step":5,"process":"Questionnaire 3"},
                                        "questionnaire": { #overwrite questionnaire field
                                            "$mergeObjects": [ #Merging the object to Root
                                            "$$ROOT.questionnaire",data #$$ROOT refers to current object.Query["$$ROOT.serviceDetails",updateObject]
                                    
                                            ]
                                        }
                                        }
                                    }
                                    ],
                                    upsert=True)
                            return Response({"message": "Successfully Updated","user_id":pk})
                        elif (clear_vision == False) and (data["current_career_choice"]==1):
                            query = f"I currently hold a {seniority}{role} position within the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} organization. My goal is to advance to a higher level of hierarchy. So take into account my current seniority :{seniority} and evaluate my related work experience {work_experience} and 'tech_skills' inside each 'work_experience' ,certifications{certifications}. Timeline is a crucial factor in my decision. Play the role of a career guidance expert and suggest 3 potential career paths(key:'career_paths') that would help me gain relevant skills to achieve this goal by considering the timeline of {timeline} days(s). For each career_paths(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'), Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to(key:'domain'), type of organization(key:'company_type'), and the achievable hierarchy levels (key:'rank' #Mention only the 'level/seniority' and not the 'role') within {timeline} days(s). Return the response in JSON format without additional explanations."
                        elif (clear_vision == False) and (data["current_career_choice"]==2):
                            stream_interest = data["career_stream_of_interest"]
                            query = f"I currently hold a {seniority}{role} position within the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} organization. Evaluate my related work experience {work_experience} and 'tech_skills' inside each 'work_experience'  and certifications{certifications}. My career stream of interest is focused around {stream_interest}.Timeline is a crucial factor in my decision. As a career guidance expert suggest 3 potential career paths(key:'career_paths') that would help me gain relevant skills to achieve this goal considering the timeline of {timeline} days(s). For each career_paths(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'), Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to(key:'domain'), type of organization(key:'company_type'), and the achievable hierarchy levels (key:'rank' #Mention only the 'level/seniority' and not the 'role') within {timeline} days(s). Return the response in JSON format without additional explanations."
                        
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
                        cost=tokens["Total Cost (USD)"]
                        numeric_value = float(cost.split('$')[1])
                        cost_details={
                                        "runway_recommendation_cost":cost,
                                        "created_on":datetime.datetime.now()
                                    }
                        cost_data["fixed_costs"]["runway_recommendation"].append(cost_details)
                        total_cost_data=cost_data["fixed_costs"]["total_cost"]
                        value=float(total_cost_data.split('$')[1])+numeric_value
                        cost_data["fixed_costs"]["total_cost"]=f"${str(value)}"
                        Cost_Details.update_one({'user_id': pk}, {'$set': cost_data})
                        response = json.loads(response)
                        runway_structure = restructure_job_recommendation(response)
                        runway_structure['current_role']=current_role
                        print(response)
                        users_registration.update_one({'_id': ObjectId(pk)},{'$set': {'runway_recommendation': runway_structure}}) 
                     except json.JSONDecodeError:
                        return Response({"response":"Please try again"},status = status.HTTP_400_BAD_REQUEST)
                     except ServiceUnavailableError:
                        return Response({"response":"The server is overloaded or not ready yet"},status = status.HTTP_400_BAD_REQUEST)
                     except RateLimitError: 
                        return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)       
                    users_registration.update_one({'_id': ObjectId(pk)}, 
                                        [
                                    {
                                        "$addFields": {
                                        "updated_at": datetime.datetime.now(),   
                                        "onboarding_process":{"step":5,"process":"Questionnaire 3"},
                                        "questionnaire": { #overwrite questionnaire field
                                            "$mergeObjects": [ #Merging the object to Root
                                            "$$ROOT.questionnaire",data #$$ROOT refers to current object.Query["$$ROOT.serviceDetails",updateObject]
                                    
                                            ]
                                        }
                                        }
                                    }
                                    ],
                                    upsert=True)
                    return Response({"message": "Successfully Updated","user_id":pk},status = status.HTTP_200_OK)
                    

                else:
                    users_registration.update_one({'_id': ObjectId(pk)}, 
                                        [
                                    {
                                        "$addFields": {
                                        "updated_at": datetime.datetime.now(),
                                        "questionnaire": { #overwrite questionnaire field
                                            "$mergeObjects": [ #Merging the object to Root
                                            "$$ROOT.questionnaire",data #$$ROOT refers to current object.Query["$$ROOT.serviceDetails",updateObject]
                                    
                                            ]
                                        }
                                        }
                                    }
                                    ],
                                    upsert=True)
                    timeline = data["career_runway_duration"]
                    current_role = questionnaire["career_runway_role_description"]
                    clear_vision=data["clear_vision_for_next_career_runway"]
                    industry = current_role["sector"]
                    seniority= current_role["rank"]
                    role = current_role["role"]
                    company_type = current_role["company_type"]
                    function = current_role["function"]
                    domain = current_role["domain"]
                    work_experience = resume_details["experience"]
                    certifications = resume_details["certifications_and_courses"]
                    if clear_vision== False:
                        users_registration.update_one({'_id': ObjectId(pk)}, {'$set': {
                                        "questionnaire.initiated_steps_towards_next_goal": "",
                                        "questionnaire.list_significant_actions_taken": []
                                    }})
                    if timeline < 24:
                     
                     try: 
                        timeline = int(timeline * 30)
                        users_registration.update_one({'_id': ObjectId(pk)},{'$set': {"questionnaire.consider_intermediate_role": ""}})
                        if (data["clear_vision_for_next_career_runway"] == True):
                            return Response({"message": "Successfully Updated","user_id":pk})
                        elif (clear_vision == False) and (data["current_career_choice"]==1):
                            query = f"I currently hold a {seniority}{role} position within the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} organization. My goal is to advance to a higher level of hierarchy. So take into account my current seniority :{seniority} and evaluate my related work experience {work_experience} and 'tech_skills' inside each 'work_experience' ,certifications{certifications}. Timeline is a crucial factor in my decision. Play the role of a career guidance expert and suggest 3 potential career paths(key:'career_paths') that would help me gain relevant skills to achieve this goal by considering the timeline of {timeline} days(s). For each career_paths(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'), Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to(key:'domain'), type of organization(key:'company_type'), and the achievable hierarchy levels (key:'rank' #Mention only the 'level/seniority' and not the 'role') within {timeline} days(s). Return the response in JSON format without additional explanations."
                        elif (clear_vision == False) and (data["current_career_choice"]==2):
                            stream_interest = data["career_stream_of_interest"]
                            query = f"I currently hold a {seniority}{role} position within the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} organization. Evaluate my related work experience {work_experience} and 'tech_skills' inside each 'work_experience'  and certifications{certifications}. My career stream of interest is focused around {stream_interest}.Timeline is a crucial factor in my decision. As a career guidance expert suggest 3 potential career paths(key:'career_paths') that would help me gain relevant skills to achieve this goal considering the timeline of {timeline} days(s). For each career_paths(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'), Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to(key:'domain'), type of organization(key:'company_type'), and the achievable hierarchy levels (key:'rank' #Mention only the 'level/seniority' and not the 'role') within {timeline} days(s). Return the response in JSON format without additional explanations."
                        
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
                        cost=tokens["Total Cost (USD)"]
                        numeric_value = float(cost.split('$')[1])
                        cost_details={
                                        "runway_recommendation_cost":cost,
                                        "created_on":datetime.datetime.now()
                                    }
                        cost_data["fixed_costs"]["runway_recommendation"].append(cost_details)
                        total_cost_data=cost_data["fixed_costs"]["total_cost"]
                        value=float(total_cost_data.split('$')[1])+numeric_value
                        cost_data["fixed_costs"]["total_cost"]=f"${str(value)}"
                        Cost_Details.update_one({'user_id': pk}, {'$set': cost_data})
                        response = json.loads(response)
                        runway_structure = restructure_job_recommendation(response)
                        runway_structure['current_role']=current_role
                        print(response)
                        users_registration.update_one({'_id': ObjectId(pk)},{'$set': {'runway_recommendation': runway_structure}}) 
                     except json.JSONDecodeError:
                        return Response({"response":"Please try again"},status = status.HTTP_400_BAD_REQUEST)
                     except ServiceUnavailableError:
                        return Response({"response":"The server is overloaded or not ready yet"},status = status.HTTP_400_BAD_REQUEST)
                     except RateLimitError: 
                        return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)       
                    return Response({"message": "Successfully Updated","user_id":pk},status = status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": "An error occured","error" :str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

'''Questionnaire Screen 4'''
class Questionnaire_4(APIView):
    def get(self, request, pk):
        try:
            # Retrieve the profile document
            profile = users_registration.find_one({'_id': ObjectId(pk)})
            if profile:
                user_id=profile["_id"]
                questionnaire = profile.get('questionnaire', {})
                if questionnaire:
                    extracted_data = {
                        "initiated_steps_towards_next_goal": questionnaire.get("initiated_steps_towards_next_goal"),
                        "list_significant_actions_taken": questionnaire.get("list_significant_actions_taken")
                    }
                    return Response({"user_id":str(user_id),"questionnaire": extracted_data})
                else:
                    return Response({"message": "Questionnaire not available"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"message": "No data found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occured","error" :str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self,request):
        try:
            request_data=request.body
            data=json.loads(request_data)
            pk=data['user_id']
            profile = users_registration.find_one({'_id': ObjectId(pk)})
            resume_details = resume_data.find_one({'user_id': pk})
            cost_data = Cost_Details.find_one({'user_id': pk})
            if not profile:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
            questionnaire=profile.get("questionnaire",{})
            onboarding_process = profile.get("onboarding_process", {})
            onboarding_status = onboarding_process.get("step", 0)
            
            data.pop("user_id")
            fields_to_check = ["initiated_steps_towards_next_goal"]
            if data:
                if any(key not in questionnaire or questionnaire.get(key) == "" for key in fields_to_check):
                    
                    timeline = questionnaire["career_runway_duration"]
                    timeline = int(timeline * 30)

                    current_role = questionnaire["career_runway_role_description"]
        
                    industry = current_role["sector"]
                    seniority= current_role["rank"]
                    role = current_role["role"]
                    company_type = current_role["company_type"]
                    function = current_role["function"]
                    domain = current_role["domain"]

                    targeted_role = questionnaire["role_at_end_of_career_runway"]
                    industry_target = targeted_role["sector"]
                    seniority_target= targeted_role["rank"]
                    domain_target = targeted_role["domain"]
                    company_type_target = targeted_role["company_type"]
                    function_target = targeted_role["function"]

                    work_experience = resume_details["experience"]
                    certifications = resume_details["certifications_and_courses"]
                    if (questionnaire["clear_vision_for_next_career_runway"] == True) and ("consider_intermediate_role" in questionnaire): 
                        
                        if (questionnaire["consider_intermediate_role"]== True):
                            if data["initiated_steps_towards_next_goal"] == True:
                                query = f"I am currently in a {seniority}{role} position in the {industry} sector, working as a {function} and in the domain {domain} at a {company_type} company. My specific focus is on {domain_target} in a {seniority_target} position within the {industry_target} sector, to {function_target} at a {company_type_target} company. I am planning my next career steps. Timeline is a crucial gfactor in my decision. So please evaluate my work experience {work_experience} and 'tech_skills' inside each 'work_experience', and certifications {certifications}, and suggest the next 3 career paths (key:'career_paths') related to the {domain_target} which could be achieved within {timeline} day(s). For each career_paths (key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'), specific Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to(key:'domain'),specify  type of company (key:'company_type'), hierarchy level (key:'rank' #Mention only the 'level/seniority' and not the 'role')), and recommend one suitable intermediate role (key:'intermediate_roles') that can help me bridge the gap to reach my 'role'. Then, for each intermediate_roles(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify its Sector (key:'sector'), specific Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to (key:'domain'),type of company (key:'company_type'), and hierarchy level (key:'rank'#Mention only the 'level/seniority' and not the 'role')). Please provide the response in proper JSON format without explanations."
                            else:
                                actions_taken = data["list_significant_actions_taken"]
                                query = f"I am currently in a {seniority}{role} position in the {industry} sector, working as a {function} and in the domain {domain} at a {company_type} company. My specific focus is on {domain_target} in a {seniority_target} position within the {industry_target} sector, to {function_target} at a {company_type_target} company. I am planning my next career steps. Timeline is a crucial gfactor in my decision. So please evaluate my work experience {work_experience} and 'tech_skills' inside each 'work_experience',certifications {certifications} and significant actions taken towards next career path {actions_taken}, and suggest the next 3 career paths (key:'career_paths') related to the {domain_target} which could be achieved within {timeline} day(s). For each career_paths (key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'),specific Function/Role within the sector (key:'function'),specify the Domain the 'role' belongs to(key:'domain'), type of company (key:'company_type'), hierarchy level (key:'rank' #Mention only the 'level/seniority' and not the 'role'), and recommend one suitable intermediate role (key:'intermediate_roles') that can help me bridge the gap to reach my 'role'. Then, for each intermediate_roles(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify its Sector (key:'sector'), specific Function/Role within the sector (key:'function'),specify the Domain the 'role' belongs to (key:'domain'), type of company (key:'company_type'), and hierarchy level (key:'rank'#Mention only the 'level/seniority' and not the 'role')). Please provide the response in proper JSON format without explanations."
                        else:
                            if data["initiated_steps_towards_next_goal"] == False:
                                query = f"In my current role, I have a {seniority}{role} position in the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} company. My primary focus is on {domain_target} in a {seniority_target} position within the {industry_target} sector, where I serve as a {function_target} at a {company_type_target} company. I am looking for my next career move. Timeline is a crucial factor in my decision. so please evaluate my work experience {work_experience} and 'tech_skills' inside each 'work_experience' and certifications {certifications}, and suggest the next 3 career paths (key:'career_paths') related to {domain_target} in a timeline of {timeline} day(s). For each career_paths(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'), specific Function/Role within the sector (key:'function'),specify the Domain the 'role' belongs to(key:'domain'), type of organization (key:'company_type'), and achievable hierarchy level(key:'rank' #Mention only the 'level/seniority' and not the 'role') within {timeline} day(s). Please provide the response in JSON format without explanations."        
                            else:
                                actions_taken = data["list_significant_actions_taken"]
                                query = f"In my current role, I have a {seniority}{role} position in the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} company. My primary focus is on {domain_target} in a {seniority_target} position within the {industry_target} sector, where I serve as a {function_target} at a {company_type_target} company. I am looking for my next career move. Timeline is a crucial factor in my decision. so please evaluate my work experience {work_experience} and 'tech_skills' inside each 'work_experience',certifications {certifications}, and significant actions taken towards next career path {actions_taken}, and suggest the next 3 career paths (key:'career_paths') related to {domain_target} in a timeline of {timeline} day(s). For each career_paths(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'), specific Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to(key:'domain'),type of organization (key:'company_type'), and achievable hierarchy level(key:'rank'#Mention only the 'level/seniority' and not the 'role') within {timeline} day(s). Please provide the response in JSON format without explanations."
                    else:
                        if data["initiated_steps_towards_next_goal"] == False:
                            query = f"In my current role, I have a {seniority}{role} position in the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} company. My primary focus is on {domain_target} in a {seniority_target} position within the {industry_target} sector, where I serve as a {function_target} at a {company_type_target} company. I am looking for my next career move. Timeline is a crucial factor in my decision. so please evaluate my work experience {work_experience} and 'tech_skills' inside each 'work_experience' and certifications {certifications}, and suggest the next 3 career paths (key:'career_paths') related to {domain_target} in a timeline of {timeline} day(s). For each career_paths(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'), specific Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to(key:'domain'),type of organization (key:'company_type'), and achievable hierarchy level(key:'rank'#Mention only the 'level/seniority' and not the 'role') within {timeline} day(s). Please provide the response in JSON format without explanations."        
                        else:
                            actions_taken = data["list_significant_actions_taken"]
                            query = f"In my current role, I have a {seniority}{role} position in the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} company. My primary focus is on {domain_target} in a {seniority_target} position within the {industry_target} sector, where I serve as a {function_target} at a {company_type_target} company. I am looking for my next career move. Timeline is a crucial factor in my decision. so please evaluate my work experience {work_experience} and 'tech_skills' inside each 'work_experience',certifications {certifications}, and significant actions taken towards next career path {actions_taken}, and suggest the next 3 career paths (key:'career_paths') related to {domain_target} in a timeline of {timeline} day(s). For each career_paths(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'), specific Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to(key:'domain'),type of organization (key:'company_type'), and achievable hierarchy level(key:'rank'#Mention only the 'level/seniority' and not the 'role') within {timeline} day(s). Please provide the response in JSON format without explanations."
                            
                    try: 
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
                        cost=tokens["Total Cost (USD)"]
                        numeric_value = float(cost.split('$')[1])
                        cost_details={
                                    "runway_recommendation_cost":cost,
                                    "created_on":datetime.datetime.now()
                                    }
                        cost_data["fixed_costs"]["runway_recommendation"].append(cost_details)
                        total_cost_data=cost_data["fixed_costs"]["total_cost"]
                        value=float(total_cost_data.split('$')[1])+numeric_value
                        cost_data["fixed_costs"]["total_cost"]=f"${str(value)}"
                        Cost_Details.update_one({'user_id': pk}, {'$set': cost_data})
                        response = json.loads(response)
                        runway_structure = restructure_job_recommendation(response)
                        runway_structure['current_role']=current_role
                        users_registration.update_one({'_id': ObjectId(pk)},{'$set': {'runway_recommendation': runway_structure}}) 
                    except json.JSONDecodeError:
                        return Response({"response":"Please try again"},status = status.HTTP_400_BAD_REQUEST)
                    except ServiceUnavailableError:
                        return Response({"response":"The server is overloaded or not ready yet"},status = status.HTTP_400_BAD_REQUEST)
                    except RateLimitError: 
                        return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)       
                    users_registration.update_one({'_id': ObjectId(pk)}, 
                                        [
                                    {
                                        "$addFields": {
                                        "updated_at": datetime.datetime.now(),
                                        "onboarding_process":{"step":7,"process":"Questionnaire 4"},
                                        "questionnaire": { #overwrite questionnaire field
                                            "$mergeObjects": [ #Merging the object to Root
                                            "$$ROOT.questionnaire",data #$$ROOT refers to current object.Query["$$ROOT.serviceDetails",updateObject]
                                    
                                            ]
                                        }
                                        }
                                    }
                                    ],
                                    upsert=True)
                    return Response({"message": "Successfully Updated","user_id":pk},status = status.HTTP_200_OK)
                    
                else:
                    users_registration.update_one({'_id': ObjectId(pk)}, 
                                        [
                                    {
                                        "$addFields": {
                                        "updated_at": datetime.datetime.now(),
                                        "questionnaire": { #overwrite questionnaire field
                                            "$mergeObjects": [ #Merging the object to Root
                                            "$$ROOT.questionnaire",data #$$ROOT refers to current object.Query["$$ROOT.serviceDetails",updateObject]
                                    
                                            ]
                                        }
                                        }
                                    }
                                    ],
                                    upsert=True)
                    timeline = questionnaire["career_runway_duration"]
                    timeline = int(timeline * 30)

                    current_role = questionnaire["career_runway_role_description"]
        
                    industry = current_role["sector"]
                    seniority= current_role["rank"]
                    role = current_role["role"]
                    company_type = current_role["company_type"]
                    function = current_role["function"]
                    domain = current_role["domain"]

                    targeted_role = questionnaire["role_at_end_of_career_runway"]
                    industry_target = targeted_role["sector"]
                    seniority_target= targeted_role["rank"]
                    domain_target = targeted_role["domain"]
                    company_type_target = targeted_role["company_type"]
                    function_target = targeted_role["function"]

                    work_experience = resume_details["experience"]
                    certifications = resume_details["certifications_and_courses"]
                    if (questionnaire["clear_vision_for_next_career_runway"] == True) and ("consider_intermediate_role" in questionnaire): 
                        
                        if (questionnaire["consider_intermediate_role"]== True):
                            if data["initiated_steps_towards_next_goal"] == True:
                                query = f"I am currently in a {seniority}{role} position in the {industry} sector, working as a {function} and in the domain {domain} at a {company_type} company. My specific focus is on {domain_target} in a {seniority_target} position within the {industry_target} sector, to {function_target} at a {company_type_target} company. I am planning my next career steps. Timeline is a crucial gfactor in my decision. So please evaluate my work experience {work_experience} and 'tech_skills' inside each 'work_experience', and certifications {certifications}, and suggest the next 3 career paths (key:'career_paths') related to the {domain_target} which could be achieved within {timeline} day(s). For each career_paths (key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'), specific Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to(key:'domain'),specify  type of company (key:'company_type'), hierarchy level (key:'rank' #Mention only the 'level/seniority' and not the 'role')), and recommend one suitable intermediate role (key:'intermediate_roles') that can help me bridge the gap to reach my 'role'. Then, for each intermediate_roles(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify its Sector (key:'sector'), specific Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to (key:'domain'),type of company (key:'company_type'), and hierarchy level (key:'rank'#Mention only the 'level/seniority' and not the 'role')). Please provide the response in proper JSON format without explanations."
                            else:
                                actions_taken = data["list_significant_actions_taken"]
                                query = f"I am currently in a {seniority}{role} position in the {industry} sector, working as a {function} and in the domain {domain} at a {company_type} company. My specific focus is on {domain_target} in a {seniority_target} position within the {industry_target} sector, to {function_target} at a {company_type_target} company. I am planning my next career steps. Timeline is a crucial gfactor in my decision. So please evaluate my work experience {work_experience} and 'tech_skills' inside each 'work_experience',certifications {certifications} and significant actions taken towards next career path {actions_taken}, and suggest the next 3 career paths (key:'career_paths') related to the {domain_target} which could be achieved within {timeline} day(s). For each career_paths (key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'),specific Function/Role within the sector (key:'function'),specify the Domain the 'role' belongs to(key:'domain'), type of company (key:'company_type'), hierarchy level (key:'rank' #Mention only the 'level/seniority' and not the 'role'), and recommend one suitable intermediate role (key:'intermediate_roles') that can help me bridge the gap to reach my 'role'. Then, for each intermediate_roles(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify its Sector (key:'sector'), specific Function/Role within the sector (key:'function'),specify the Domain the 'role' belongs to (key:'domain'), type of company (key:'company_type'), and hierarchy level (key:'rank'#Mention only the 'level/seniority' and not the 'role')). Please provide the response in proper JSON format without explanations."
                        else:
                            if data["initiated_steps_towards_next_goal"] == False:
                                query = f"In my current role, I have a {seniority}{role} position in the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} company. My primary focus is on {domain_target} in a {seniority_target} position within the {industry_target} sector, where I serve as a {function_target} at a {company_type_target} company. I am looking for my next career move. Timeline is a crucial factor in my decision. so please evaluate my work experience {work_experience} and 'tech_skills' inside each 'work_experience' and certifications {certifications}, and suggest the next 3 career paths (key:'career_paths') related to {domain_target} in a timeline of {timeline} day(s). For each career_paths(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'), specific Function/Role within the sector (key:'function'),specify the Domain the 'role' belongs to(key:'domain'), type of organization (key:'company_type'), and achievable hierarchy level(key:'rank' #Mention only the 'level/seniority' and not the 'role') within {timeline} day(s). Please provide the response in JSON format without explanations."        
                            else:
                                actions_taken = data["list_significant_actions_taken"]
                                query = f"In my current role, I have a {seniority}{role} position in the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} company. My primary focus is on {domain_target} in a {seniority_target} position within the {industry_target} sector, where I serve as a {function_target} at a {company_type_target} company. I am looking for my next career move. Timeline is a crucial factor in my decision. so please evaluate my work experience {work_experience} and 'tech_skills' inside each 'work_experience',certifications {certifications}, and significant actions taken towards next career path {actions_taken}, and suggest the next 3 career paths (key:'career_paths') related to {domain_target} in a timeline of {timeline} day(s). For each career_paths(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'), specific Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to(key:'domain'),type of organization (key:'company_type'), and achievable hierarchy level(key:'rank'#Mention only the 'level/seniority' and not the 'role') within {timeline} day(s). Please provide the response in JSON format without explanations."
                    else:
                        if data["initiated_steps_towards_next_goal"] == False:
                            query = f"In my current role, I have a {seniority}{role} position in the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} company. My primary focus is on {domain_target} in a {seniority_target} position within the {industry_target} sector, where I serve as a {function_target} at a {company_type_target} company. I am looking for my next career move. Timeline is a crucial factor in my decision. so please evaluate my work experience {work_experience} and 'tech_skills' inside each 'work_experience' and certifications {certifications}, and suggest the next 3 career paths (key:'career_paths') related to {domain_target} in a timeline of {timeline} day(s). For each career_paths(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'), specific Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to(key:'domain'),type of organization (key:'company_type'), and achievable hierarchy level(key:'rank'#Mention only the 'level/seniority' and not the 'role') within {timeline} day(s). Please provide the response in JSON format without explanations."        
                        else:
                            actions_taken = data["list_significant_actions_taken"]
                            query = f"In my current role, I have a {seniority}{role} position in the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} company. My primary focus is on {domain_target} in a {seniority_target} position within the {industry_target} sector, where I serve as a {function_target} at a {company_type_target} company. I am looking for my next career move. Timeline is a crucial factor in my decision. so please evaluate my work experience {work_experience} and 'tech_skills' inside each 'work_experience',certifications {certifications}, and significant actions taken towards next career path {actions_taken}, and suggest the next 3 career paths (key:'career_paths') related to {domain_target} in a timeline of {timeline} day(s). For each career_paths(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'), specific Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to(key:'domain'),type of organization (key:'company_type'), and achievable hierarchy level(key:'rank'#Mention only the 'level/seniority' and not the 'role') within {timeline} day(s). Please provide the response in JSON format without explanations."
                            
                try: 
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
                    cost=tokens["Total Cost (USD)"]
                    numeric_value = float(cost.split('$')[1])
                    cost_details={
                                "runway_recommendation_cost":cost,
                                "created_on":datetime.datetime.now()
                                }
                    cost_data["fixed_costs"]["runway_recommendation"].append(cost_details)
                    total_cost_data=cost_data["fixed_costs"]["total_cost"]
                    value=float(total_cost_data.split('$')[1])+numeric_value
                    cost_data["fixed_costs"]["total_cost"]=f"${str(value)}"
                    Cost_Details.update_one({'user_id': pk}, {'$set': cost_data})
                    response = json.loads(response)
                    runway_structure = restructure_job_recommendation(response)
                    runway_structure['current_role']=current_role
                    print(response)
                    users_registration.update_one({'_id': ObjectId(pk)},{'$set': {'runway_recommendation': runway_structure}}) 
                except json.JSONDecodeError:
                    return Response({"response":"Please try again"},status = status.HTTP_400_BAD_REQUEST)
                except ServiceUnavailableError:
                    return Response({"response":"The server is overloaded or not ready yet"},status = status.HTTP_400_BAD_REQUEST)
                except RateLimitError: 
                    return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)       
                return Response({"message": "Successfully Updated","user_id":pk},status = status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": "An error occured","error" :str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

'''Intermediate Role'''
class Intermediate_role(APIView):

    def get(self, request, pk):
        try:
            # Retrieve the profile document
            profile = users_registration.find_one({'_id': ObjectId(pk)})
            if profile:
                user_id=profile["_id"]
                questionnaire = profile.get('questionnaire', {})
                if questionnaire:
                    extracted_data = {
                        "consider_intermediate_role": questionnaire.get("consider_intermediate_role")
                    }
                    return Response({"user_id":str(user_id),"questionnaire": extracted_data})
                else:
                    return Response({"message": "Questionnaire not available"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"message": "No data found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occured","error" :str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self,request):
        try:
            request_data=request.body
            data=json.loads(request_data)
            pk=data['user_id']
            profile = users_registration.find_one({'_id': ObjectId(pk)})
            resume_details = resume_data.find_one({'user_id': pk})
            cost_data = Cost_Details.find_one({'user_id': pk})
            if not profile:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
            questionnaire=profile.get("questionnaire",{})
            onboarding_process = profile.get("onboarding_process", {})
            onboarding_status = onboarding_process.get("step", 0)
            
            data.pop("user_id")
            fields_to_check = ["consider_intermediate_role"]
            if data:
                if any(key not in questionnaire or questionnaire.get(key) == "" for key in fields_to_check):
                    
                    timeline = questionnaire["career_runway_duration"]
                    timeline = int(timeline * 30)

                    current_role = questionnaire["career_runway_role_description"]
        
                    industry = current_role["sector"]
                    seniority= current_role["rank"]
                    role = current_role["role"]
                    company_type = current_role["company_type"]
                    function = current_role["function"]
                    domain = current_role["domain"]
                    work_experience = resume_details["experience"]
                    certifications = resume_details["certifications_and_courses"]
                    if questionnaire["clear_vision_for_next_career_runway"] == False:
                     try:   
                        print("inter tryy") 
                        if (questionnaire["current_career_choice"]==1) and (data["consider_intermediate_role"]==True) :
                            print("Intermediate 1")
                            query = f"In my current role, I hold a {seniority}{role} position in the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} company. My goal is to advance in my career to a higher level of hierarchy. So take into account my current seniority :{seniority} and evaluate my related work experience {work_experience} and 'tech_skills' inside each 'work_experience' ,certifications{certifications}. Timeline is a crucial factor in my decision. As a career guidance expert suggest 3 potential career paths(key:'career_paths') that would help me gain relevant skills to achieve this goal considering the timeline of {timeline} day(s) For each career_paths(key:'role' # specify a role(and not integer) without mentioning it's rank/seniority in this key), specify its Sector (key:'sector'), specific Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to (key:'domain'),type of organization (key:'company_type'), and the target hierarchy level (key:'rank' #Mention only the 'level/seniority' and not the 'role'). Additionally, suggest one suitable intermediate role (key:'intermediate_roles') that would help bridge the gap to reach my 'role'. Then, for each intermediate_roles (key:'role' # specify a role(and not integer) without mentioning it's rank/seniority in this key), specify its Sector (key:'sector'), specific Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to (key:'domain'),type of company (key:'company_type'), and hierarchy level (key:'rank' #Mention only the 'level/seniority' and not the 'role'). Please provide the response in proper JSON format without explanations."
                        elif (questionnaire["current_career_choice"]==1) and (data["consider_intermediate_role"]==False) :
                            print("Intermediate 2")
                            query = f"I currently hold a {seniority}{role} position within the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} organization. My goal is to advance to a higher level of hierarchy. So take into account my current seniority :{seniority} and evaluate my related work experience {work_experience} and 'tech_skills' inside each 'work_experience' ,certifications{certifications}. Timeline is a crucial factor in my decision. Play the role of a career guidance expert and suggest 3 potential career paths(key:'career_paths') that would help me gain relevant skills to achieve this goal by considering the timeline of {timeline} day(s). For each career_paths(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'), Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to (key:'domain'),type of organization(key:'company_type'), and the achievable hierarchy levels (key:'rank' #Mention only the 'level/seniority' and not the 'role') within {timeline} day(s). Return the response in JSON format without additional explanations."
                        elif (questionnaire["current_career_choice"]==2) and (data["consider_intermediate_role"]==True) :
                            print("Intermediate 3")
                            stream_interest = questionnaire["career_stream_of_interest"]
                            query = f"I currently hold a {seniority}{role} position within the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} organization. Evaluate my related work experience {work_experience} and 'tech_skills' inside each 'work_experience'  and certifications{certifications}. My career stream of interest is focused around {stream_interest}.Timeline is a crucial factor in my decision. As a career guidance expert suggest 3 potential career paths(key:'career_paths') that would help me gain relevant skills to achieve this goal considering the timeline of {timeline} day(s). For each career_paths(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'), Function/Role within the sector (key:'function'),specify the Domain the 'role' belongs to (key:'domain'), type of organization(key:'company_type'), and the achievable hierarchy levels (key:'rank' #Mention only the 'level/seniority' and not the 'role') within {timeline} day(s). Additionally, suggest one suitable intermediate role (key:'intermediate_roles') that would help bridge the gap to reach my 'role'. Then, for each intermediate_roles (key:'role' # specify a role(and not integer) without mentioning it's rank/seniority in this key), specify its Sector (key:'sector'), specific Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to (key:'domain'), type of company (key:'company_type'), and hierarchy level (key:'rank' #Mention only the 'level/seniority' and not the 'role').  Return the response in JSON format without additional explanations."
                        elif (questionnaire["current_career_choice"]==2) and (data["consider_intermediate_role"]==False) :
                            print("Intermediate 4")
                            stream_interest = questionnaire["career_stream_of_interest"]
                            query = f"I currently hold a {seniority}{role} position within the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} organization. Evaluate my related work experience {work_experience} and 'tech_skills' inside each 'work_experience'  and certifications{certifications}. My career stream of interest is focused around {stream_interest}.Timeline is a crucial factor in my decision. As a career guidance expert suggest 3 potential career paths(key:'career_paths') that would help me gain relevant skills to achieve this goal considering the timeline of {timeline} day(s). For each career_paths(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'), Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to (key:'domain'),type of organization(key:'company_type'), and the achievable hierarchy levels (key:'rank' #Mention only the 'level/seniority' and not the 'role') within {timeline} day(s). Return the response in JSON format without additional explanations."
                    
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
                        cost=tokens["Total Cost (USD)"]
                        numeric_value = float(cost.split('$')[1])
                        cost_details={
                                    "runway_recommendation_cost":cost,
                                    "created_on":datetime.datetime.now()
                                    }
                        cost_data["fixed_costs"]["runway_recommendation"].append(cost_details)
                        total_cost_data=cost_data["fixed_costs"]["total_cost"]
                        value=float(total_cost_data.split('$')[1])+numeric_value
                        cost_data["fixed_costs"]["total_cost"]=f"${str(value)}"
                        Cost_Details.update_one({'user_id': pk}, {'$set': cost_data})
                        response = json.loads(response)
                        runway_structure = restructure_job_recommendation(response)
                        runway_structure['current_role']=current_role
                        users_registration.update_one({'_id': ObjectId(pk)},{'$set': {'runway_recommendation': runway_structure}}) 
                     except json.JSONDecodeError:
                        return Response({"message":"Please try again"},status = status.HTTP_400_BAD_REQUEST)
                     except ServiceUnavailableError:
                        return Response({"message":"The server is overloaded or not ready yet"},status = status.HTTP_400_BAD_REQUEST)
                     except RateLimitError: 
                        return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)
                    users_registration.update_one({'_id': ObjectId(pk)}, 
                                        [
                                    {
                                        "$addFields": {
                                        "updated_at": datetime.datetime.now(),   
                                        "onboarding_process":{"step":6,"process":"Intermediate Role"},
                                        "questionnaire": { #overwrite questionnaire field
                                            "$mergeObjects": [ #Merging the object to Root
                                            "$$ROOT.questionnaire",data #$$ROOT refers to current object.Query["$$ROOT.serviceDetails",updateObject]
                                    
                                            ]
                                        }
                                        }
                                    }
                                    ],
                                    upsert=True)
                    return Response({"message": "Successfully Updated","user_id":pk},status = status.HTTP_200_OK)
                    
                else:
                    users_registration.update_one({'_id': ObjectId(pk)}, 
                                        [
                                    {
                                        "$addFields": {
                                        "updated_at": datetime.datetime.now(),
                                        "questionnaire": { #overwrite questionnaire field
                                            "$mergeObjects": [ #Merging the object to Root
                                            "$$ROOT.questionnaire",data #$$ROOT refers to current object.Query["$$ROOT.serviceDetails",updateObject]
                                    
                                            ]
                                        }
                                        }
                                    }
                                    ],
                                    upsert=True)
                    timeline = questionnaire["career_runway_duration"]
                    timeline = int(timeline * 30)

                    current_role = questionnaire["career_runway_role_description"]
        
                    industry = current_role["sector"]
                    seniority= current_role["rank"]
                    role = current_role["role"]
                    company_type = current_role["company_type"]
                    function = current_role["function"]
                    domain = current_role["domain"]
                    work_experience = resume_details["experience"]
                    certifications = resume_details["certifications_and_courses"]
                    if questionnaire["clear_vision_for_next_career_runway"] == False:
                     try:   
                        print("inter tryy") 
                        if (questionnaire["current_career_choice"]==1) and (data["consider_intermediate_role"]==True) :
                            print("Intermediate 1")
                            query = f"In my current role, I hold a {seniority}{role} position in the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} company. My goal is to advance in my career to a higher level of hierarchy. So take into account my current seniority :{seniority} and evaluate my related work experience {work_experience} and 'tech_skills' inside each 'work_experience' ,certifications{certifications}. Timeline is a crucial factor in my decision. As a career guidance expert suggest 3 potential career paths(key:'career_paths') that would help me gain relevant skills to achieve this goal considering the timeline of {timeline} day(s) For each career_paths(key:'role' # specify a role(and not integer) without mentioning it's rank/seniority in this key), specify its Sector (key:'sector'), specific Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to (key:'domain'),type of organization (key:'company_type'), and the target hierarchy level (key:'rank' #Mention only the 'level/seniority' and not the 'role'). Additionally, suggest one suitable intermediate role (key:'intermediate_roles') that would help bridge the gap to reach my 'role'. Then, for each intermediate_roles (key:'role' # specify a role(and not integer) without mentioning it's rank/seniority in this key), specify its Sector (key:'sector'), specific Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to (key:'domain'),type of company (key:'company_type'), and hierarchy level (key:'rank' #Mention only the 'level/seniority' and not the 'role'). Please provide the response in proper JSON format without explanations."
                        elif (questionnaire["current_career_choice"]==1) and (data["consider_intermediate_role"]==False) :
                            print("Intermediate 2")
                            query = f"I currently hold a {seniority}{role} position within the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} organization. My goal is to advance to a higher level of hierarchy. So take into account my current seniority :{seniority} and evaluate my related work experience {work_experience} and 'tech_skills' inside each 'work_experience' ,certifications{certifications}. Timeline is a crucial factor in my decision. Play the role of a career guidance expert and suggest 3 potential career paths(key:'career_paths') that would help me gain relevant skills to achieve this goal by considering the timeline of {timeline} day(s). For each career_paths(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'), Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to (key:'domain'),type of organization(key:'company_type'), and the achievable hierarchy levels (key:'rank' #Mention only the 'level/seniority' and not the 'role') within {timeline} day(s). Return the response in JSON format without additional explanations."
                        elif (questionnaire["current_career_choice"]==2) and (data["consider_intermediate_role"]==True) :
                            print("Intermediate 3")
                            stream_interest = questionnaire["career_stream_of_interest"]
                            query = f"I currently hold a {seniority}{role} position within the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} organization. Evaluate my related work experience {work_experience} and 'tech_skills' inside each 'work_experience'  and certifications{certifications}. My career stream of interest is focused around {stream_interest}.Timeline is a crucial factor in my decision. As a career guidance expert suggest 3 potential career paths(key:'career_paths') that would help me gain relevant skills to achieve this goal considering the timeline of {timeline} day(s). For each career_paths(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'), Function/Role within the sector (key:'function'),specify the Domain the 'role' belongs to (key:'domain'), type of organization(key:'company_type'), and the achievable hierarchy levels (key:'rank' #Mention only the 'level/seniority' and not the 'role') within {timeline} day(s). Additionally, suggest one suitable intermediate role (key:'intermediate_roles') that would help bridge the gap to reach my 'role'. Then, for each intermediate_roles (key:'role' # specify a role(and not integer) without mentioning it's rank/seniority in this key), specify its Sector (key:'sector'), specific Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to (key:'domain'), type of company (key:'company_type'), and hierarchy level (key:'rank' #Mention only the 'level/seniority' and not the 'role').  Return the response in JSON format without additional explanations."
                        elif (questionnaire["current_career_choice"]==2) and (data["consider_intermediate_role"]==False) :
                            print("Intermediate 4")
                            stream_interest = questionnaire["career_stream_of_interest"]
                            query = f"I currently hold a {seniority}{role} position within the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} organization. Evaluate my related work experience {work_experience} and 'tech_skills' inside each 'work_experience'  and certifications{certifications}. My career stream of interest is focused around {stream_interest}.Timeline is a crucial factor in my decision. As a career guidance expert suggest 3 potential career paths(key:'career_paths') that would help me gain relevant skills to achieve this goal considering the timeline of {timeline} day(s). For each career_paths(key:'role' #specify a role(and not integer) without mentioning it's rank/seniority in this key), specify it's Sector (key:'sector'), Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to (key:'domain'),type of organization(key:'company_type'), and the achievable hierarchy levels (key:'rank' #Mention only the 'level/seniority' and not the 'role') within {timeline} day(s). Return the response in JSON format without additional explanations."
                    
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
                        cost=tokens["Total Cost (USD)"]
                        numeric_value = float(cost.split('$')[1])
                        cost_details={
                                    "runway_recommendation_cost":cost,
                                    "created_on":datetime.datetime.now()
                                    }
                        cost_data["fixed_costs"]["runway_recommendation"].append(cost_details)
                        total_cost_data=cost_data["fixed_costs"]["total_cost"]
                        value=float(total_cost_data.split('$')[1])+numeric_value
                        cost_data["fixed_costs"]["total_cost"]=f"${str(value)}"
                        Cost_Details.update_one({'user_id': pk}, {'$set': cost_data})
                        response = json.loads(response)
                        runway_structure = restructure_job_recommendation(response)
                        runway_structure['current_role']=current_role
                        print(response)
                        users_registration.update_one({'_id': ObjectId(pk)},{'$set': {'runway_recommendation': runway_structure}}) 
                     except json.JSONDecodeError:
                        return Response({"message":"Please try again"},status = status.HTTP_400_BAD_REQUEST)
                     except ServiceUnavailableError:
                        return Response({"message":"The server is overloaded or not ready yet"},status = status.HTTP_400_BAD_REQUEST)
                     except RateLimitError: 
                        return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)       
                    return Response({"message": "Successfully Updated","user_id":pk},status = status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": "An error occured","error" :str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

'''Runway_Recommendation'''
class Runway_Recommendation(APIView):
    def get(self, request, pk):
        try:
            # Retrieve the profile document
            profile = users_registration.find_one({'_id': ObjectId(pk)})
            if profile:
                user_id = profile["_id"]
                runway_recommendation = profile.get('runway_recommendation', {})
                if runway_recommendation:
                    career_paths = runway_recommendation.get("career_paths", [])                    
                    for path in career_paths:
                        path["current_role"] = runway_recommendation["current_role"]
                    
                    return Response({"user_id": str(user_id), "runway_recommendation": {"career_paths": career_paths}})
                else:
                    return Response({"message": "recommendation not available"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"message": "No data found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

'''Check Intermediate Role for Custom Runway'''
class CheckIntermediateRole(APIView):
    def post(self,request):
        try:
            request_data=request.body
            data=json.loads(request_data)
            targeted_role = data['targeted_role']
            pk=data['user_id']
            profile = users_registration.find_one({'_id': ObjectId(pk)})
            resume_details = resume_data.find_one({'user_id': pk})
            cost_data = Cost_Details.find_one({'user_id': pk})
            if not profile:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
            questionnaire=profile.get("questionnaire",{})
            if not questionnaire:
                return Response({"message": "No data found"}, status=status.HTTP_400_BAD_REQUEST)
            timeline = questionnaire["career_runway_duration"]
            consider_intermediate_role = questionnaire["consider_intermediate_role"]
            current_role = questionnaire["career_runway_role_description"]
            #if data["custom_runway"] is True:
            if timeline >= 24 and consider_intermediate_role is True :
                try:
                    industry = current_role["sector"]
                    seniority= current_role["rank"]
                    role = current_role["role"]
                    company_type = current_role["company_type"]
                    function = current_role["function"]
                    domain = current_role["domain"]

                    target_industry = targeted_role["sector"]
                    target_seniority= targeted_role["rank"]
                    target_role = targeted_role["role"]
                    target_company_type = targeted_role["company_type"]
                    target_function = targeted_role["function"]
                    target_domain = targeted_role["domain"]

                    work_experience = resume_details["experience"]
                    certifications = resume_details["certifications_and_courses"]
                    query = f"In my current role, I hold a {seniority}{role} position in the {industry} sector, specializing in {function} and in the domain {domain} at a {company_type} company. And I wanna become a {target_seniority}{target_role} position in the {target_industry} sector, specializing in {target_function} in the domain {target_domain} at a {target_company_type} company.My goal is to advance in my career to the {target_role}. So take into account my current seniority :{seniority} and evaluate my related work experience {work_experience} and 'tech_skills' inside each 'work_experience' ,certifications{certifications}. Timeline is a crucial factor in my decision. As a career guidance expert suggest one suitable intermediate role (key:'intermediate_roles') that would help bridge the gap between my current role{role}  and the target role {target_role}. Then, for each intermediate_roles (key:'role' # specify a role(and not integer) without mentioning it's rank/seniority in this key), specify its Sector (key:'sector'), specific Function/Role within the sector (key:'function'), specify the Domain the 'role' belongs to (key:'domain'), type of company (key:'company_type'), and hierarchy level (key:'rank' #Mention only the 'level/seniority' and not the 'role'). Please provide the response in proper JSON format without explanations."
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
                    cost=tokens["Total Cost (USD)"]
                    numeric_value = float(cost.split('$')[1])
                    cost_details={
                                    "custom_runway_cost":cost,
                                    "created_on":datetime.datetime.now()
                                }
                    cost_data["fixed_costs"]["custom_runway"].append(cost_details)
                    total_cost_data=cost_data["fixed_costs"]["total_cost"]
                    value=float(total_cost_data.split('$')[1])+numeric_value
                    cost_data["fixed_costs"]["total_cost"]=f"${str(value)}"
                    Cost_Details.update_one({'user_id': pk}, {'$set': cost_data})
                    intermediate_roles = json.loads(response)
                    return Response({"intermediate_roles": intermediate_roles["intermediate_roles"],"user_id":pk},status = status.HTTP_200_OK)
                except json.JSONDecodeError:
                    return Response({"message":"Please try again"},status = status.HTTP_400_BAD_REQUEST)
                except ServiceUnavailableError:
                    return Response({"message":"The server is overloaded or not ready yet"},status = status.HTTP_400_BAD_REQUEST)
                except RateLimitError: 
                    return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)       
            else:
                return Response({"intermediate_roles": [],
                                   "message": "No suitable intermediate roles","user_id":pk},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": "An error occured","error" :str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


"""selected user journey"""
class Selected_User_Journey(APIView):
    def get(self, request, pk):
        try:
            # Retrieve the profile document
            profile = users_registration.find_one({'_id': ObjectId(pk)})
            if profile:
                user_id = profile["_id"]
                questionnaire=profile.get("questionnaire",{})
                selected_user_journey = questionnaire['selected_user_journey']
                if selected_user_journey:
                    return Response({"user_id":str(user_id),"selected_user_journey": selected_user_journey}, status=status.HTTP_200_OK)
                else:
                    return Response({"message": "No data found"}, status=status.HTTP_400_BAD_REQUEST) 
            else:
                return Response({"message": "No data found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self,request):
        try:
            request_data=request.body
            data=json.loads(request_data)
            pk=data['user_id']
            
            resume_details = resume_data.find_one({'user_id': pk})
            if not resume_details:
                return Response({"message": "Resume details not found"}, status=status.HTTP_400_BAD_REQUEST)
            cost_data = Cost_Details.find_one({'user_id': pk})
            work_experience = resume_details["experience"]
            education_levels = resume_details["education"]
            soft_skills = resume_details["soft_skills"]
            professional_association = resume_details["professional_association"]
            achievements_and_accolades = resume_details["achievements_and_accolades"]
            certification = resume_details["certifications_and_courses"]

            profile = users_registration.find_one({'_id': ObjectId(pk)})
            if not profile:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
            questionnaire=profile.get("questionnaire",{})
            onboarding_process = profile.get("onboarding_process", {})
            onboarding_status = onboarding_process.get("step", 0)
            
            data.pop("user_id")
            fields_to_check = ["selected_user_journey"]
            if data:
                if any(key not in questionnaire for key in fields_to_check):
                    if "custom_runway" not in data:
                        return Response({"message":"custom_runway is mandatory"},status=status.HTTP_400_BAD_REQUEST)
                    
                    questionnaire=profile.get("questionnaire",{})
                    if not questionnaire:
                        return Response({"message": "No data found"}, status=status.HTTP_400_BAD_REQUEST)
                    
                    timeline = questionnaire["career_runway_duration"]
                    timeline = int(timeline * 30)
                    user_id=profile["_id"]
                    user_journey_data=data["selected_user_journey"]

                    current_role = user_journey_data["current_role"]
                    intermediate_roles = user_journey_data["intermediate_roles"]
                    targeted_role = user_journey_data["targeted_role"]
                    domain = request.META['HTTP_HOST']
                    if domain=="127.0.0.1:8000":    
                        path_1 = './Milestones Bucket_2.xlsx'
                        path_2 = './Milestones Bucket_3.xlsx'
                    else:    
                        path_1 = '/var/www/html/Backend/Milestones Bucket_2.xlsx'
                        path_2 = '/var/www/html/Backend/Milestones Bucket_3.xlsx'

                    response_1 = pd.read_excel(path_1).to_json(orient="records")
                    milestone_1 = json.loads(response_1)
                    
                    response_2 = pd.read_excel(path_2).to_json(orient="records")
                    milestone_2 = json.loads(response_2)
                    if len(intermediate_roles) == 0:
                        print("No intermediate_role")
                        query = f"""My current role is {current_role} and my long-term goal is to become a {targeted_role} in {timeline} day(s). As a professional career guidance expert, I'd like you to assess my qualifications: {soft_skills}, {education_levels}, {work_experience}, {certification}, {professional_association} and {achievements_and_accolades}. Please do not return these details in the response.
                            For the transition from current_role to long_term_goal, I need specific milestones and actions. These milestones should help me assess my soft skills, education levels, technical skills, certifications, and work experience. I'm looking for up to a maximum of 8 milestones(# root key ‘milestones’)  
                            For each milestone, provide the following details:
                            1. Title (key: 'title'): Ensure the milestone title to be very specific and sum up the actions(#max 100 characters).
                            2. Milestone Description (key: 'milestone_description'): Describe the milestone.
                            3. Milestone Type (key: 'type'): Specify if it's a milestone or targeted_role.
                            4. Actions (key: 'actions'): Suggest up to maximum 3 actions to achieve the milestone.
                            5.From {milestone_1} analyse milestone['milestone_category'] and milestone['actions_to_track_and_complete'] details into consideration while generating the milestones and  while generating particular actions  for that milestone(Please do not return these  milestone['milestone_category'] and milestone['actions_to_track_and_complete'] value in milestone 'title' and action 'title' response). But specify the milestone category(Key:category) to which each milestones belong to.
                            6. consider the long_term_goal['role'] to be one among the suggested milestones(#except the fact that title(#max 100 characters) for these alone should be the role name and actions 'title'(#max 150 characters) under this milestone 'title' be like from {milestone_2} milestone['milestone_category']). I want you to Divide the total timeline of {timeline} day(s) (key : ‘timeline’ format: X day(s) suitably across these milestones). For each milestone, allocate a duration for each action (key: 'duration' (format:X day(s) by dividing the ‘duration’ within the milestone ‘timeline’)). Also,provide the ’title’ (# specifying any online courses, platforms, projects, or institutes along with the title  that can help achieve the action)and ‘description’ for each action.
                            Additionally, suggest up to three critical enablers (key: 'enablers') for each milestone, chosen from the following list: [Growth mindset, Self-discipline, Optimism, Proactivity, Reflective thinking, Self-awareness, Attitude, Strategic thinking, Goal-setting, Creativity, Analytical thinking, Financial literacy, Learning agility, Leadership, Adaptability, Flexibility, Cultural competence, Conflict resolution, Active listening, Decision-making, Relationship building, Feedback-seeking].
                            Please return the response in JSON format without any explanations."""
                        
                    elif len(intermediate_roles) == 1:
                        print("1 intermediate_role")
                        query = f"""My current role is {current_role} and my long-term goal is to become a {targeted_role} with the intermediate role of {intermediate_roles} in {timeline} day(s). As a professional career guidance expert, I'd like you to assess my qualifications: {soft_skills}, {education_levels}, {work_experience},{certification},{professional_association} and {achievements_and_accolades}. Please do not return these details in the response.
                        For the transition from {current_role} to {intermediate_roles}, and then from {intermediate_roles} to {targeted_role}, I need some milestones and actions to help me achieve the next 'role'. These milestones should help me assess my soft skills, education levels, technical skills, certifications, and work experience. I'm looking for up to a maximum of 8 milestones(# root key ‘milestones’)  
                        For each milestone, provide the following details:
                        1. Title (key: 'title'): Ensure the milestone title to be very specific and sum up the actions(#max 100 characters).
                        2. Milestone Description (key: 'milestone_description'): Describe the milestone.
                        3. Milestone Type (key: 'type'): Specify if it's a milestone, intermediate_role, or targeted_role.
                        4. Actions (key: 'actions'): Suggest up to maximum 3 actions to achieve the milestone.
                        5.From {milestone_1} you can  take this milestone['milestone_category'] and milestone['actions_to_track_and_complete']details into consideration while generating the milestones and  while generating particular actions  for that milestone(Please do not return these  milestone['milestone_category'] and milestone['actions_to_track_and_complete'] value in milestone 'title' and action 'title' response). But specify the milestone category(Key:category) to which each milestones belong to.
                        6. considering the intermediate_role['role'] and long_term_goal['role'] to be one among the suggested milestones(#except the fact that title(#max 100 characters) for these alone should be the role name and actions 'title'(#max 150 characters) under this milestone 'title' be like from {milestone_2} milestone['milestone_category']).I want you to Divide the total timeline of {timeline} day(s) (key : ‘timeline’ format: X day(s) suitably across these milestones). For each milestone, allocate a duration for each action (key: 'duration' (format:X day(s) by dividing the ‘duration’ within the milestone ‘timeline’)). Also,provide the ’title’ (# specifying any online courses, platforms, projects, or institutes along with the title  that can help achieve the action)and ‘description’ for each action.
                        Additionally, suggest up to three critical enablers (key: 'enablers') for each milestone, chosen from the following list: [Growth mindset, Self-discipline, Optimism, Proactivity, Reflective thinking, Self-awareness, Attitude, Strategic thinking, Goal-setting, Creativity, Analytical thinking, Financial literacy, Learning agility, Leadership, Adaptability, Flexibility, Cultural competence, Conflict resolution, Active listening, Decision-making, Relationship building, Feedback-seeking].
                        Please return the response in JSON format without any explanations.
                        """       
                    else:
                        return Response({"message":"No data found"})

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
                    cost=tokens["Total Cost (USD)"]
                    numeric_value = float(cost.split('$')[1])
                    cost_data["fixed_costs"]["nodemap_cost"]=cost
                    total_cost_data=cost_data["fixed_costs"]["total_cost"]
                    value=float(total_cost_data.split('$')[1])+numeric_value
                    cost_data["fixed_costs"]["total_cost"]=f"${str(value)}"
                    cost_data["fixed_costs"]["updated_on"]=datetime.datetime.now()
                    nodemap = json.loads(response)
                    nodemap_restructure = restructure_nodemap(nodemap["milestones"],user_id,data['selected_user_journey'])
                    dashboard = dashboard_data.find_one({'user_id':pk})
                    if not dashboard:
                        nodemap_id=dashboard_data.insert_one(nodemap_restructure).inserted_id
                        cost_data["nodemap_id"]=str(nodemap_id)
                        Cost_Details.update_one({'user_id': pk}, {'$set': cost_data})
                    else:
                        
                        dashboard_data.update_one({'user_id':pk},{'$set': nodemap_restructure})
                    users_registration.update_one({'_id': ObjectId(pk)}, 
                                        [
                                    {
                                        "$addFields": {
                                        "updated_at": datetime.datetime.now(),  
                                        "onboarding_process":{"step":8,"process":"Runway Recommendations"},
                                        "questionnaire": { #overwrite questionnaire field
                                            "$mergeObjects": [ #Merging the object to Root
                                            "$$ROOT.questionnaire",data #$$ROOT refers to current object.Query["$$ROOT.serviceDetails",updateObject]
                                    
                                            ]
                                        }
                                        }
                                    }
                                    ],
                                    upsert=True)
                    return Response({"message": "Successfully Updated","user_id":pk},status = status.HTTP_200_OK)     
                    
                else:
                    if "custom_runway" not in data:
                        return Response({"message":"custom_runway is mandatory"},status=status.HTTP_400_BAD_REQUEST)
                    users_registration.update_one({'_id': ObjectId(pk)}, 
                                        [
                                    {
                                        "$addFields": {
                                        "updated_at": datetime.datetime.now(),    
                                        "questionnaire": { #overwrite questionnaire field
                                            "$mergeObjects": [ #Merging the object to Root
                                            "$$ROOT.questionnaire",data #$$ROOT refers to current object.Query["$$ROOT.serviceDetails",updateObject]
                                    
                                            ]
                                        }
                                        }
                                    }
                                    ],
                                    upsert=True)
                    questionnaire=profile.get("questionnaire",{})
                    if not questionnaire:
                        return Response({"message": "No data found"}, status=status.HTTP_400_BAD_REQUEST)
                    
                    timeline = questionnaire["career_runway_duration"]
                    timeline = int(timeline * 30)
                    user_id=profile["_id"]
                    user_journey_data=data["selected_user_journey"]

                    current_role = user_journey_data["current_role"]
                    intermediate_roles = user_journey_data["intermediate_roles"]
                    targeted_role = user_journey_data["targeted_role"]
                    domain = request.META['HTTP_HOST']
                    if domain=="127.0.0.1:8000":    
                        path_1 = './Milestones Bucket_2.xlsx'
                        path_2 = './Milestones Bucket_3.xlsx'
                    else:    
                        path_1 = '/var/www/html/Backend/Milestones Bucket_2.xlsx'
                        path_2 = '/var/www/html/Backend/Milestones Bucket_3.xlsx'

                    response_1 = pd.read_excel(path_1).to_json(orient="records")
                    milestone_1 = json.loads(response_1)
                    
                    response_2 = pd.read_excel(path_2).to_json(orient="records")
                    milestone_2 = json.loads(response_2)
                    if len(intermediate_roles) == 0:
                        print("No intermediate_role")
                        query = f"""My current role is {current_role} and my long-term goal is to become a {targeted_role} in {timeline} day(s). As a professional career guidance expert, I'd like you to assess my qualifications: {soft_skills}, {education_levels}, {work_experience}, {certification}, {professional_association} and {achievements_and_accolades}. Please do not return these details in the response.
                            For the transition from current_role to long_term_goal, I need specific milestones and actions. These milestones should help me assess my soft skills, education levels, technical skills, certifications, and work experience. I'm looking for up to a maximum of 8 milestones(# root key ‘milestones’)  
                            For each milestone, provide the following details:
                            1. Title (key: 'title'): Ensure the milestone title to be very specific and sum up the actions(#max 100 characters).
                            2. Milestone Description (key: 'milestone_description'): Describe the milestone.
                            3. Milestone Type (key: 'type'): Specify if it's a milestone or targeted_role.
                            4. Actions (key: 'actions'): Suggest up to maximum 3 actions to achieve the milestone.
                            5.From {milestone_1} analyse milestone['milestone_category'] and milestone['actions_to_track_and_complete'] details into consideration while generating the milestones and  while generating particular actions  for that milestone(Please do not return these  milestone['milestone_category'] and milestone['actions_to_track_and_complete'] value in milestone 'title' and action 'title' response). But specify the milestone category(Key:category) to which each milestones belong to.
                            6. consider the long_term_goal['role'] to be one among the suggested milestones(#except the fact that title(#max 100 characters) for these alone should be the role name and actions 'title'(#max 150 characters) under this milestone 'title' be like from {milestone_2} milestone['milestone_category']). I want you to Divide the total timeline of {timeline} day(s) (key : ‘timeline’ format: X day(s) suitably across these milestones). For each milestone, allocate a duration for each action (key: 'duration' (format:X day(s) by dividing the ‘duration’ within the milestone ‘timeline’)). Also,provide the ’title’ (# specifying any online courses, platforms, projects, or institutes along with the title  that can help achieve the action)and ‘description’ for each action.
                            Additionally, suggest up to three critical enablers (key: 'enablers') for each milestone, chosen from the following list: [Growth mindset, Self-discipline, Optimism, Proactivity, Reflective thinking, Self-awareness, Attitude, Strategic thinking, Goal-setting, Creativity, Analytical thinking, Financial literacy, Learning agility, Leadership, Adaptability, Flexibility, Cultural competence, Conflict resolution, Active listening, Decision-making, Relationship building, Feedback-seeking].
                            Please return the response in JSON format without any explanations."""
                        
                    elif len(intermediate_roles) == 1:
                        print("1 intermediate_role")
                        query = f"""My current role is {current_role} and my long-term goal is to become a {targeted_role} with the intermediate role of {intermediate_roles} in {timeline} day(s). As a professional career guidance expert, I'd like you to assess my qualifications: {soft_skills}, {education_levels}, {work_experience},{certification},{professional_association} and {achievements_and_accolades}. Please do not return these details in the response.
                        For the transition from {current_role} to {intermediate_roles}, and then from {intermediate_roles} to {targeted_role}, I need some milestones and actions to help me achieve the next 'role'. These milestones should help me assess my soft skills, education levels, technical skills, certifications, and work experience. I'm looking for up to a maximum of 8 milestones(# root key ‘milestones’)  
                        For each milestone, provide the following details:
                        1. Title (key: 'title'): Ensure the milestone title to be very specific and sum up the actions(#max 100 characters).
                        2. Milestone Description (key: 'milestone_description'): Describe the milestone.
                        3. Milestone Type (key: 'type'): Specify if it's a milestone, intermediate_role, or targeted_role.
                        4. Actions (key: 'actions'): Suggest up to maximum 3 actions to achieve the milestone.
                        5.From {milestone_1} you can  take this milestone['milestone_category'] and milestone['actions_to_track_and_complete']details into consideration while generating the milestones and  while generating particular actions for that milestone(Please do not return these  milestone['milestone_category'] and milestone['actions_to_track_and_complete'] value in milestone 'title' and action 'title' response). But specify the milestone category(Key:category) to which each milestones belong to.
                        6. considering the intermediate_role['role'] and long_term_goal['role'] to be one among the suggested milestones(#except the fact that title(#max 100 characters) for these alone should be the role name and actions 'title'(#max 150 characters) under this milestone 'title' be like from {milestone_2} milestone['milestone_category']).I want you to Divide the total timeline of {timeline} day(s) (key : ‘timeline’ format: X day(s) suitably across these milestones). For each milestone, allocate a duration for each action (key: 'duration' (format:X day(s) by dividing the ‘duration’ within the milestone ‘timeline’)). Also,provide the ’title’ (# specifying any online courses, platforms, projects, or institutes along with the title  that can help achieve the action)and ‘description’ for each action.
                        Additionally, suggest up to three critical enablers (key: 'enablers') for each milestone, chosen from the following list: [Growth mindset, Self-discipline, Optimism, Proactivity, Reflective thinking, Self-awareness, Attitude, Strategic thinking, Goal-setting, Creativity, Analytical thinking, Financial literacy, Learning agility, Leadership, Adaptability, Flexibility, Cultural competence, Conflict resolution, Active listening, Decision-making, Relationship building, Feedback-seeking].
                        Please return the response in JSON format without any explanations.
                        """

                    else:
                        return Response({"message":"No data found"})

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
                    cost=tokens["Total Cost (USD)"]
                    numeric_value = float(cost.split('$')[1])
                    cost_data["fixed_costs"]["nodemap_cost"]=cost
                    total_cost_data=cost_data["fixed_costs"]["total_cost"]
                    value=float(total_cost_data.split('$')[1])+numeric_value
                    cost_data["fixed_costs"]["total_cost"]=f"${str(value)}"
                    cost_data["fixed_costs"]["updated_on"]=datetime.datetime.now()
                    nodemap = json.loads(response)
                    nodemap_restructure = restructure_nodemap(nodemap["milestones"],user_id,data['selected_user_journey'])
                    dashboard = dashboard_data.find_one({'user_id':pk})
                    if not dashboard:
                        nodemap_id=dashboard_data.insert_one(nodemap_restructure).inserted_id
                        cost_data["nodemap_id"]=str(nodemap_id)
                        Cost_Details.update_one({'user_id': pk}, {'$set': cost_data})
                    else:
                        dashboard_data.update_one({'user_id':pk},{'$set': nodemap_restructure})
                    return Response({"message": "Successfully Updated","user_id":pk},status = status.HTTP_200_OK)     
        except json.JSONDecodeError:
            return Response({"message":"Please try again"},status=status.HTTP_400_BAD_REQUEST)
        except ServiceUnavailableError:
            return Response({"message":"The server is overloaded or not ready yet"},status=status.HTTP_400_BAD_REQUEST)           
        except RateLimitError: 
            return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)       
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class current_role(APIView):
    def get(self, request, pk):
        # try:
            # Retrieve the profile documen
            user = users_registration.find_one({'_id': ObjectId(pk)})
            if user:
                user_id=user["_id"]
                questionnaire_data=user.get("questionnaire",{})
                # print(questionnaire_data)
                role_description=questionnaire_data.get("career_runway_role_description",{})
                if role_description:
                    return Response({"user_id":str(user_id),"current_role": role_description})
                else:
                    return Response({"message": "Curent emploment data not available"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"message": "No data found"}, status=status.HTTP_400_BAD_REQUEST)
        # except Exception as e:
        #     return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProgressAPI(APIView):
    def get(self,request,id):
        user=users_registration.find_one({"_id":ObjectId(id)})
        if user is None:
            return Response({"message": "No User found"}, status=status.HTTP_400_BAD_REQUEST)

        onboarding_process = user.get("onboarding_process", {})
        onboarding_step = onboarding_process.get("step", 0)
        process = onboarding_process.get("process", {})

        if onboarding_step !=8:
            return Response({"onboarding_step": onboarding_step, "onboarding_status":1}, status=status.HTTP_200_OK)
        else:
            return Response({"onboarding_step": onboarding_step, "onboarding_status":2}, status=status.HTTP_200_OK)



class ResumeUploadView(APIView):
    def post(self,request):
      try:
        data=request.data
        user_id=data.get("user_id")
        user_resume=data.get("resume")
        user=users_registration.find_one({"_id":ObjectId(user_id)})
        if user is None:
            return Response({"message":"User Not Found"},status=status.HTTP_400_BAD_REQUEST)
        cost_data = Cost_Details.find_one({'user_id': user_id})
        onboarding_process = user.get("onboarding_process", {})
        onboarding_status = onboarding_process.get("step", 0)
        uploaded_file = request.FILES['resume']
        resume_obj = resume_data.find_one({'user_id':user_id})
        file_name = uploaded_file.name
        extension = file_name.split('.')[-1]
        if not (extension.endswith('pdf') | extension.endswith('docx')):
            return Response({"message":"unsupported file format"},status=status.HTTP_400_BAD_REQUEST)
        response,cost = resume_reader(uploaded_file,extension)
        if response == 1:
            return Response({"message":"File size exceeds 2MB"},status=status.HTTP_400_BAD_REQUEST)
        if response is False:
            return Response({"message":"The file appears to be empty. Kindly provide the correct resume file for upload."},status=status.HTTP_400_BAD_REQUEST) 
        if cost_data:
            numeric_value = float(cost.split('$')[1])
            cost_details={"resume_upload_cost":cost,
                        "created_on":datetime.datetime.now()}
            cost_data["fixed_costs"]["resume_upload"].append(cost_details)
            total_cost_details=cost_data["fixed_costs"]["total_cost"]
            value=float(total_cost_details.split('$')[1])+numeric_value
            cost_data["fixed_costs"]["total_cost"]=f"${str(value)}"
            Cost_Details.update_one({'user_id': user_id}, {'$set': cost_data})
        else:
            cost_data={
                    "user_id": user_id,
                    "fixed_costs": {
                        "resume_upload":[{"resume_upload_cost":cost,
                                        "created_on":datetime.datetime.now()}],
                        "runway_recommendation": [],
                        "custom_runway":[],
                        "nodemap_cost": "",
                        "total_cost": cost
                    },
                    "variable_costs": {
                    "edit_milestone": {
                    "total_cost": "0",
                    "edit_milestone_cost":[]},
                    "add_milestone": {
                        "total_cost": "0",
                        "add_milestone_cost":[]},
                    "add_actions": {
                    "total_cost": "0",
                    "add_action_cost":[]
                    },
                    "edit_actions": {
                    "total_cost": "0",
                    "edit_action_cost":[]
                    },
                    
                        "edit_intermediate": {
                        "total_cost":"0",
                        "edit_intermediate_cost":[]},
                    
                        "add_intermediate": {
                        "total_cost":"0",
                        "add_intermediate_cost":[]
                        },
                        "edit_northstar": {
                        "total_cost":"0",
                        "edit_northstar_cost":[]
                        }
                    },
                    "fixed_variable_sum": "0",
                    }   
            Cost_Details.insert_one(cost_data).inserted_id
        s3_storage = S3Boto3Storage()
        file_path =f'resume/{user_id}.{extension}'
        with uploaded_file.open(mode='rb') as file:
            # Now, you can read the content of the file using file.read()
           content = file.read()
           saved_file_path = s3_storage.save(file_path, ContentFile(content))
           file_url = s3_storage.url(saved_file_path)

        city = response["city"]
        country = response["country"]
        current_role = response["current_role"]
        education_levels = response["education_levels"]
        education_levels = validate_education(education_levels)

        work_experience = response["work_experience"]
        work_experience = validate_experience(work_experience)

        soft_skills = response["soft_skills"]
        soft_skills = validate_soft_skills(soft_skills)

        hobbies_interests = response["hobbies"]
        hobbies_interests = validate_hobbies(hobbies_interests)

        certifications = response["certifications_held"]
        certifications = validate_certifications(certifications)

        associations = response["professional_associations"]
        associations = validate_professional_associations(associations)

        achievements = response["achievements_and_accolades"]
        achievements = validate_achievements(achievements)

        restructured_data = {
            "user_id": user_id,
            "current_occupation":current_role,
            "city" : city,
            "country" : country,
            "soft_skills":soft_skills,
            "hobbies":hobbies_interests,
            "education":education_levels,
            "experience":work_experience,
            "certifications_and_courses":certifications,
            "professional_association":associations,
            "achievements_and_accolades":achievements,
            "updated_at":datetime.datetime.now(),
            "created_at":datetime.datetime.now()

        }
        
        data = {
        "resume":file_url,
        "updated_at":datetime.datetime.now(),
        }

        if "resume" not in user:
            users_registration.update_one({'_id': ObjectId(user_id)}, {'$set': data})
            profile_id = resume_data.insert_one(restructured_data)
            restructured_data.pop('_id')
            users_registration.update_one({'_id': ObjectId(user_id)}, {'$set': {"onboarding_process":{"step":3,"process":"Career Overview"}}})
            return Response({"message":"resume upload sucessfully","profile_id":str(profile_id.inserted_id),"resume_response":restructured_data},status=status.HTTP_200_OK)
        else:
            users_registration.update_one({'_id': ObjectId(user_id)}, {'$set': data})
            id = resume_obj['_id']
            resume_data.update_one({"_id":ObjectId(id)},{'$set': restructured_data})
            return Response({"message":"resume upload sucessfully","profile_id":str(id),"resume_response":restructured_data},status=status.HTTP_200_OK)

      except json.JSONDecodeError:
        return Response({"message":"Please upload the resume again"},status=status.HTTP_400_BAD_REQUEST)
      except InvalidRequestError: # Raised when gpt token limit is exceeded 
        return Response({"message":"File is too large to process. Please review your resume and try to make it more concise"},status=status.HTTP_400_BAD_REQUEST)
      except ServiceUnavailableError:
        return Response({"message":"The server is overloaded or not ready yet"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
      except RateLimitError: 
            return Response({"message":"You exceeded your current quota, please check your plan and billing details"}, status=status.HTTP_400_BAD_REQUEST)       

class my_profile(APIView):
   def get(self, request, id):
        try:
            # Convert ObjectId to string
            user_data = resume_data.find_one({"user_id": str(id)})
            if user_data:
                user_data['_id'] = str(user_data['_id'])
                
                # Check if "experience" and "professional_association" exist and are not None
                if "experience" in user_data and user_data["experience"]:
                    for item in user_data["experience"]:
                        # Calculate duration using the existing function
                        start_date = item.get("start_date")
                        end_date = item.get("end_date")
                        if end_date == "Present":
                            end_date = datetime.datetime.now().strftime("%B %Y")  # Set end_date to the current date
                        item["duration"] = calculate_duration(start_date, end_date)
                
                if "professional_association" in user_data and user_data["professional_association"]:
                    for item in user_data["professional_association"]:
                        # Calculate duration using the existing function
                        start_date = item.get("start_date")
                        end_date = item.get("end_date")
                        if end_date == "Present":
                            end_date = datetime.datetime.now().strftime("%B %Y")  # Set end_date to the current date
                        item["duration"] = calculate_duration(start_date, end_date)

                return Response({"user_id": str(id), "Profile Data": user_data}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "User not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Log the exception for debugging
            return Response({"message": "An error occurred", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


''' Edit Hobbies'''
class EditHobbiesAndInterests(APIView):
    def get(self, request, pk):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            if profile:
                hobbies=profile['hobbies']
                if hobbies is None:
                    return Response({"message":"No hobbies found"}, status=status.HTTP_400_BAD_REQUEST)
                return Response({"Hobbies": hobbies})
            else:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, pk):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            if not profile:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
            new_hobbies = request.data.get("hobbies", [])
            current_hobbies = profile.get("hobbies", [])

            if len(current_hobbies) + len(new_hobbies) > 10:
                return Response({"message": "Maximum 10 hobbies allowed"}, status=status.HTTP_400_BAD_REQUEST)

            new_hobbies = [hobby.lower() for hobby in new_hobbies]
            current_hobbies = [hobby.lower() for hobby in current_hobbies] 

            for hb in new_hobbies:
                if hb in current_hobbies:
                    return Response({"message": f"{hb} already present"})
                
            update_data = {
            '$push': {'hobbies': {'$each': new_hobbies}},
            '$set': {'updated_at': datetime.datetime.now()}
        }
            resume_data.update_one({'user_id': str(pk)}, update_data)
            return Response({"message": "Successfully Updated"})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
    def delete(self, request, pk):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            
            if profile is None:
                return Response({"message":"No User Found"}, status=status.HTTP_400_BAD_REQUEST)

            hobbies = profile.get('hobbies', [])

            # Get the list of skills to delete from the request body
            hobbies_to_delete = request.data.get('hobbies_to_delete', [])

            hobbies = [hobby.lower() for hobby in hobbies]
            hobbies_to_delete = [hobby.lower() for hobby in hobbies_to_delete]

            # Iterate over the skills to delete and remove them from the list
            for hobbies_interest in hobbies_to_delete:
                if hobbies_interest in hobbies:
                    hobbies.remove(hobbies_interest)
                else:
                    return Response({"message":"Given hobbies not found"},status=status.HTTP_400_BAD_REQUEST)

            # Update the profile document with the modified technical_skills list
            resume_data.update_one({'user_id': str(pk)}, {'$set': {'hobbies': hobbies}})

            return Response({"message": "Skills deleted successfully"})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


''' Edit Soft Skills'''
class EditSoftSkills(APIView):
    def get(self, request, pk):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            
            if profile:
                soft_skills=profile['soft_skills']
                if soft_skills is None:
                    return Response({"message":"No soft skills found"}, status=status.HTTP_400_BAD_REQUEST)
                return Response({"soft_skills": soft_skills})
            else:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, pk):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            if not profile:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
            new_skills_list = request.data.get("soft_skills", [])
            current_soft_skills = profile.get("soft_skills", [])

            if len(current_soft_skills) + len(new_skills_list) > 10:
                return Response({"message": "Maximum 10 soft skills allowed"}, status=status.HTTP_400_BAD_REQUEST)


            new_skills_list = [soft_skill.lower() for soft_skill in new_skills_list]
            current_soft_skills = [skill.lower() for skill in current_soft_skills]
            

            for hb in new_skills_list:
                if hb in current_soft_skills:
                    return Response({"message": f"{hb} already present"})
            update_data = {
            '$push': {'soft_skills': {'$each': new_skills_list}},
            '$set': {'updated_at': datetime.datetime.now()}
        }
            resume_data.update_one({'user_id': str(pk)}, update_data)
            return Response({"message": "Successfully Updated"})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
    def delete(self, request, pk):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})

            if profile is None:
                return Response({"message":"No User Found"}, status=status.HTTP_400_BAD_REQUEST)

            soft_skills = profile.get('soft_skills', [])

            # Get the list of skills to delete from the request body
            skills_to_delete = request.data.get('skills_to_delete', [])

            soft_skills = [soft_skill.lower() for soft_skill in soft_skills]
            skills_to_delete = [skill.lower() for skill in skills_to_delete]

            # Iterate over the skills to delete and remove them from the list
            for skill in skills_to_delete:
                if skill in soft_skills:
                    soft_skills.remove(skill)
                else:
                    return Response({"message":"Given Skills not found"},status=status.HTTP_400_BAD_REQUEST)

            # Update the profile document with the modified technical_skills list
            resume_data.update_one({'user_id': str(pk)}, {'$set': {'soft_skills': soft_skills}})

            return Response({"message": "Skills deleted successfully"})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


''' Edit Experience'''
class EditExperience(APIView):
    # def get(self, request, pk):
    #     try:
    #         # Retrieve the profile document
    #         profile = resume_data.find_one({'user_id': str(pk)})
            
    #         if profile:
    #             experience=profile['experience']
    #             if not experience:
    #                 return Response({"experience": []})
    #             sorted_experiences = sorted(experience, key=lambda x: datetime.datetime.strptime(x.get('start_date', 'January 1900'), "%B %Y"), reverse=True)
    #             for experience in sorted_experiences:
    #                 experience.pop("updated_at", None)
    #                 experience.pop("created_at", None)
    #             return Response({"experience": sorted_experiences})
    #         else:
    #             return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
    #     except Exception as e:
    #         return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, pk):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})

            if profile:
                experience = profile.get('experience', [])

                if experience is None:
                    experience = []

                def get_start_date(record):
                    start_date = record.get('start_date')
                    if start_date is None:
                        return datetime.datetime(1900, 1, 1)  # A default date for records with null start_date
                    return datetime.datetime.strptime(start_date, "%B %Y")

                # Separate the records with "N/A" from others
                records_with_na = [record for record in experience if record.get('start_date') == "N/A"]
                records_without_na = [record for record in experience if record.get('start_date') != "N/A"]

                # Sort the records without "N/A"
                sorted_records_without_na = sorted(records_without_na, key=get_start_date, reverse=True)

                # Combine the sorted records and records with "N/A"
                sorted_experience = sorted_records_without_na + records_with_na

                for record in sorted_experience:
                    # Remove 'updated_at' and 'created_at' keys
                    start_date = record.get('start_date')
                    end_date = record.get('end_date')
                
                    if end_date == "Present":
                        end_date = datetime.datetime.now().strftime("%B %Y")  # Set end_date to the current date

                    record['duration'] = calculate_duration(start_date, end_date)
                    record.pop("updated_at", None)
                    record.pop("created_at", None)

                return Response({"experience": sorted_experience}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, pk):
        try:
                # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            if not profile:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
                
                
            experience = profile.get("experience", [])

            if experience is None:
                experience = []

            max_id = max([ach.get('id', 0) for ach in experience], default=0)

            # Increment the maximum ID to generate a unique ID for the new achievement
            unique_id = max_id + 1
                
            new_experience = {
                    "id": unique_id,
                    **request.data.get("experience"),
                    "updated_at": datetime.datetime.now(),
                    "created_at": datetime.datetime.now(),
                    "retrieved_from": "user"
                }
            tech_skills = new_experience.get("tech_skills", [])
            if len(tech_skills) > 5:
                return Response({"message": "Maximum 5 technical skills allowed"}, status=status.HTTP_400_BAD_REQUEST)

            experience.append(new_experience)
                
            profile["experience"] = experience
                
            profile["updated_at"] = datetime.datetime.now()
                
            resume_data.update_one({'user_id': str(pk)}, {'$set': profile})

            return Response({"message": "Successfully Added"})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
							
    def patch(self, request, pk, exp_id):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            if not profile:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)

            # Get the "experience" array from the profile document
            experience = profile.get("experience", [])
            # technical_skills=profile["experience"]["technical_skills"]

            # Find the "experience" document with the given ID
            updated_experience = None
            for exp in experience:
                if exp.get("id") == int(exp_id):
                    updated_experience = exp
                    break

            if updated_experience:
                # Update the fields of the "experience" document with the provided data
                updated_experience_data = request.data.get("updated_experience")
                # updated_technical_skills=request.data.get("updated_technical_skills")
                if updated_experience_data:
                    
                    updated_experience.update(updated_experience_data)
                    # updated_experience['technical_skills']=updated_technical_skills
                    updated_experience["updated_at"]=datetime.datetime.now()

                    # Update the "updated_at" field in the profile document
                    profile["updated_at"] = datetime.datetime.now()

                    # Update the entire profile document in the database
                    resume_data.update_one({'user_id': str(pk)}, {'$set': profile})

                    return Response({"message": "Successfully Updated"})
                else:
                    return Response({"message": "No data provided for update"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"message": "Experience not found"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, pk, experience_id):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            if profile is None:
                return Response({"message": "No User Found"}, status=status.HTTP_400_BAD_REQUEST)
            
            experience = profile.get('experience', [])

            experience_id = int(experience_id)

            
            found = False
            updated_experience = []

            for ach in experience:
                if ach.get('id') == experience_id:
                    found = True
                else:
                    updated_experience.append(ach)

            if not found:
                return Response({"message": "experience not found"}, status=status.HTTP_400_BAD_REQUEST)

            # Update the profile document with the modified experience list
            profile['experience'] = updated_experience
            resume_data.update_one({'user_id': str(pk)}, {'$set': profile})

            return Response({"message": "experience deleted successfully"})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


''' Edit Education'''
class EditEducation(APIView):
    # def get(self, request, pk):
    #     try:
    #         # Retrieve the profile document
    #         profile = resume_data.find_one({'user_id': str(pk)})
            
    #         if profile:
    #             education=profile['education']
    #             if not education:
    #                 return Response({"education": []})
    #             sorted_education = sorted(education, key=lambda x: datetime.datetime.strptime(x.get('start_date', 'January 1900'), "%B %Y"), reverse=True)
    #             for education in sorted_education:
    #                 education.pop("updated_at", None)
    #                 education.pop("created_at", None)
    #             return Response({"education": sorted_education})
    #         else:
    #             return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
    #     except Exception as e:
    #         return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, pk):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})

            if profile:
                education = profile.get('education', [])

                if education is None:
                    education = []

                def get_start_date(record):
                    start_date = record.get('start_date')
                    if start_date is None:
                        return datetime.datetime(1900, 1, 1)  # A default date for records with null start_date
                    return datetime.datetime.strptime(start_date, "%B %Y")

                # Separate the records with "N/A" from others
                records_with_na = [record for record in education if record.get('start_date') == "N/A"]
                records_without_na = [record for record in education if record.get('start_date') != "N/A"]

                # Sort the records without "N/A"
                sorted_records_without_na = sorted(records_without_na, key=get_start_date, reverse=True)

                # Combine the sorted records and records with "N/A"
                sorted_education = sorted_records_without_na + records_with_na

                for record in sorted_education:
                    # Remove 'updated_at' and 'created_at' keys
                    record.pop("updated_at", None)
                    record.pop("created_at", None)

                return Response({"education": sorted_education})
            else:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def post(self, request, pk):
        try:
                # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            if not profile:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
                
                
            education = profile.get("education", [])

            if education is None:
                education = []

            if len(education) >= 8:
                return Response({"message": "Maximum 8 education entries allowed"}, status=status.HTTP_400_BAD_REQUEST)

            max_id = max([ach.get('id', 0) for ach in education], default=0)

            # Increment the maximum ID to generate a unique ID for the new achievement
            unique_id = max_id + 1
                
            new_education = {
                    "id": unique_id,
                    **request.data.get("education"),
                    "updated_at": datetime.datetime.now(),
                    "created_at": datetime.datetime.now(),
                    "retrieved_from": "user"
                }

            education.append(new_education)
                
            profile["education"] = education
                
            profile["updated_at"] = datetime.datetime.now()
                
            resume_data.update_one({'user_id': str(pk)}, {'$set': profile})

            return Response({"message": "Successfully Added"})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
	
    def patch(self, request, pk, edu_id):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            if not profile:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)

            # Get the "education" array from the profile document
            education = profile.get("education", [])

            # Find the "education" document with the given ID
            updated_education = None
            for edu in education:
                if edu.get("id") == int(edu_id):
                    updated_education = edu
                    break

            if updated_education:
                # Update the fields of the "education" document with the provided data
                updated_education_data = request.data.get("updated_education")
                if updated_education_data:
                    updated_education.update(updated_education_data)
                    updated_education["updated_at"]=datetime.datetime.now()

                    # Update the "updated_at" field in the profile document
                    profile["updated_at"] = datetime.datetime.now()

                    # Update the entire profile document in the database
                    resume_data.update_one({'user_id': str(pk)}, {'$set': profile})

                    return Response({"message": "Successfully Updated"})
                else:
                    return Response({"message": "No data provided for update"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"message": "education not found"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, pk, education_id):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            if profile is None:
                return Response({"message": "No User Found"}, status=status.HTTP_400_BAD_REQUEST)
            
            education = profile.get('education', [])

            education_id = int(education_id)

            
            found = False
            updated_education = []

            for ach in education:
                if ach.get('id') == education_id:
                    found = True
                else:
                    updated_education.append(ach)

            if not found:
                return Response({"message": "education not found"}, status=status.HTTP_400_BAD_REQUEST)

            # Update the profile document with the modified education list
            profile['education'] = updated_education
            resume_data.update_one({'user_id': str(pk)}, {'$set': profile})

            return Response({"message": "education deleted successfully"})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


''' Edit Certifications'''
class EditCertifications(APIView):
    # def get(self, request, pk):
    #     try:
    #         # Retrieve the profile document
    #         profile = resume_data.find_one({'user_id': str(pk)})
            
    #         if profile:
    #             certifications_and_courses = profile.get('certifications_and_courses', [])
    #             if not certifications_and_courses:
    #                 return Response({"certifications": []})
    #             sorted_certifications = sorted(certifications_and_courses, key=lambda x: datetime.datetime.strptime(x.get('exhibited_on', 'January 1900'), "%B %Y"), reverse=True)
    #             for certification in sorted_certifications:
    #                 certification.pop("updated_at", None)
    #                 certification.pop("created_at", None)
    #             return Response({"certifications": sorted_certifications})
    #         else:
    #             return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
    #     except Exception as e:
    #         return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, pk):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})

            if profile:
                certifications_and_courses = profile.get('certifications_and_courses', [])

                if certifications_and_courses is None:
                    certifications_and_courses = []

                def get_exhibited_on(record):
                    exhibited_on = record.get('exhibited_on')
                    if exhibited_on is None:
                        return datetime.datetime(1900, 1, 1)  # A default date for records with null exhibited_on
                    return datetime.datetime.strptime(exhibited_on, "%B %Y")

                # Separate the records with "N/A" from others
                records_with_na = [record for record in certifications_and_courses if record.get('exhibited_on') == "N/A"]
                records_without_na = [record for record in certifications_and_courses if record.get('exhibited_on') != "N/A"]

                # Sort the records without "N/A"
                sorted_records_without_na = sorted(records_without_na, key=get_exhibited_on, reverse=True)

                # Combine the sorted records and records with "N/A"
                sorted_certifications_and_courses = sorted_records_without_na + records_with_na

                for record in sorted_certifications_and_courses:
                    # Remove 'updated_at' and 'created_at' keys
                    record.pop("updated_at", None)
                    record.pop("created_at", None)

                return Response({"certifications": sorted_certifications_and_courses})
            else:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, pk):
        try:
                # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            if not profile:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
                
                
            certifications_and_courses = profile.get("certifications_and_courses", [])

            if certifications_and_courses is None:
                certifications_and_courses = []

            max_id = max([ach.get('id', 0) for ach in certifications_and_courses], default=0)

            # Increment the maximum ID to generate a unique ID for the new achievement
            unique_id = max_id + 1
                
            new_certifications_and_courses = {
                    "id": unique_id,
                    **request.data.get("certifications_and_courses"),
                    "updated_at": datetime.datetime.now(),
                    "created_at": datetime.datetime.now(),
                    "retrieved_from": "user"
                }

            certifications_and_courses.append(new_certifications_and_courses)
                
            profile["certifications_and_courses"] = certifications_and_courses
                
            profile["updated_at"] = datetime.datetime.now()
                
            resume_data.update_one({'user_id': str(pk)}, {'$set': profile})

            return Response({"message": "Successfully Added"})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
    def patch(self, request, pk, cert_id):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            if not profile:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)

            # Get the "certifications_and_courses" array from the profile document
            certifications_and_courses = profile.get("certifications_and_courses", [])

            # Find the "certifications_and_courses" document with the given ID
            updated_certifications_and_courses = None
            for cert in certifications_and_courses:
                if cert.get("id") == int(cert_id):
                    updated_certifications_and_courses = cert
                    break

            if updated_certifications_and_courses:
                # Update the fields of the "certifications_and_courses" document with the provided data
                updated_certifications_and_courses_data = request.data.get("updated_certifications_and_courses")
                if updated_certifications_and_courses_data:
                    updated_certifications_and_courses.update(updated_certifications_and_courses_data)
                    updated_certifications_and_courses["updated_at"]=datetime.datetime.now()

                    # Update the "updated_at" field in the profile document
                    profile["updated_at"] = datetime.datetime.now()

                    # Update the entire profile document in the database
                    resume_data.update_one({'user_id': str(pk)}, {'$set': profile})

                    return Response({"message": "Successfully Updated"})
                else:
                    return Response({"message": "No data provided for update"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"message": "certifications_and_courses not found"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, pk, certificate_id):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            if profile is None:
                return Response({"message": "No User Found"}, status=status.HTTP_400_BAD_REQUEST)
            
            certifications_and_courses = profile.get('certifications_and_courses', [])

            certificate_id = int(certificate_id)

            
            found = False
            updated_certifications_and_courses = []

            for ach in certifications_and_courses:
                if ach.get('id') == certificate_id:
                    found = True
                else:
                    updated_certifications_and_courses.append(ach)

            if not found:
                return Response({"message": "certifications_and_courses not found"}, status=status.HTTP_400_BAD_REQUEST)

            # Update the profile document with the modified certifications_and_courses list
            profile['certifications_and_courses'] = updated_certifications_and_courses
            resume_data.update_one({'user_id': str(pk)}, {'$set': profile})

            return Response({"message": "certifications_and_courses deleted successfully"})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


'''Edit Professional Association'''
class EditProfessionalAssociationAPI(APIView):
    # def get(self, request, pk):
    #     try:
    #         # Retrieve the profile document
    #         profile = resume_data.find_one({'user_id': str(pk)})
            
    #         if profile:
    #             professional_association=profile['professional_association']
    #             if not professional_association:
    #                 return Response({"professional_association": []})
    #             sorted_professional_association = sorted(professional_association, key=lambda x: datetime.datetime.strptime(x.get('start_date', 'January 1900'), "%B %Y"), reverse=True)
    #             for professional in sorted_professional_association:
    #                 professional.pop("updated_at", None)
    #                 professional.pop("created_at", None)
    #             return Response({"professional_association": sorted_professional_association})
    #         else:
    #             return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
    #     except Exception as e:
    #         return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, pk):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})

            if profile:
                professional_association = profile.get('professional_association', [])

                if professional_association is None:
                    professional_association = []

                def get_start_date(record):
                    start_date = record.get('start_date')
                    if start_date is None:
                        return datetime.datetime(1900, 1, 1)  # A default date for records with null start_date
                    return datetime.datetime.strptime(start_date, "%B %Y")

                # Separate the records with "N/A" from others
                records_with_na = [record for record in professional_association if record.get('start_date') == "N/A"]
                records_without_na = [record for record in professional_association if record.get('start_date') != "N/A"]

                # Sort the records without "N/A"
                sorted_records_without_na = sorted(records_without_na, key=get_start_date, reverse=True)

                # Combine the sorted records and records with "N/A"
                sorted_professional_association = sorted_records_without_na + records_with_na

                for record in sorted_professional_association:
                    start_date = record.get('start_date')
                    end_date = record.get('end_date')
                
                    if end_date == "Present":
                        end_date = datetime.datetime.now().strftime("%B %Y")  # Set end_date to the current date

                    record['duration'] = calculate_duration(start_date, end_date)
                    # Remove 'updated_at' and 'created_at' keys
                    record.pop("updated_at", None)
                    record.pop("created_at", None)

                return Response({"professional_association": sorted_professional_association})
            else:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, pk):
        try:
                # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            if not profile:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
                
                
            professional_association = profile.get("professional_association", [])

            if professional_association is None:
                professional_association = []

            max_id = max([ach.get('id', 0) for ach in professional_association], default=0)

            # Increment the maximum ID to generate a unique ID for the new achievement
            unique_id = max_id + 1
                
            new_professional_association = {
                    "id": unique_id,
                    **request.data.get("professional_association"),
                    "updated_at": datetime.datetime.now(),
                    "created_at": datetime.datetime.now(),
                    "retrieved_from": "user"
                }

            professional_association.append(new_professional_association)
                
            profile["professional_association"] = professional_association
                
            profile["updated_at"] = datetime.datetime.now()
                
            resume_data.update_one({'user_id': str(pk)}, {'$set': profile})

            return Response({"message": "Successfully Added"})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, pk, prof_id):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            if not profile:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)

            # Get the "professional_association" array from the profile document
            professional_association = profile.get("professional_association", [])

            # Find the "professional_association" document with the given ID
            updated_professional_association = None
            for prof in professional_association:
                if prof.get("id") == int(prof_id):
                    updated_professional_association = prof
                    break

            if updated_professional_association:
                # Update the fields of the "professional_association" document with the provided data
                updated_professional_association_data = request.data.get("updated_professional_association")
                if updated_professional_association_data:
                    updated_professional_association.update(updated_professional_association_data)
                    updated_professional_association["updated_at"]=datetime.datetime.now()

                    # Update the "updated_at" field in the profile document
                    profile["updated_at"] = datetime.datetime.now()

                    # Update the entire profile document in the database
                    resume_data.update_one({'user_id': str(pk)}, {'$set': profile})

                    return Response({"message": "Successfully Updated"})
                else:
                    return Response({"message": "No data provided for update"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"message": "professional_association not found"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, pk, professional_id):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            if profile is None:
                return Response({"message": "No User Found"}, status=status.HTTP_400_BAD_REQUEST)
            
            professional_association = profile.get('professional_association', [])

            professional_id = int(professional_id)

            
            found = False
            updated_professional_association = []

            for ach in professional_association:
                if ach.get('id') == professional_id:
                    found = True
                else:
                    updated_professional_association.append(ach)

            if not found:
                return Response({"message": "professional_association not found"}, status=status.HTTP_400_BAD_REQUEST)

            # Update the profile document with the modified professional_association list
            profile['professional_association'] = updated_professional_association
            resume_data.update_one({'user_id': str(pk)}, {'$set': profile})

            return Response({"message": "professional_association deleted successfully"})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

'''Edit_Achievements_Accolades'''
class Edit_Achievements_Accolades_API(APIView):

    def get(self, request, pk):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})

            if profile:
                achievements_and_accolades = profile.get('achievements_and_accolades', [])

                if achievements_and_accolades is None:
                    achievements_and_accolades = []

                def get_exhibited_on(record):
                    exhibited_on = record.get('exhibited_on')
                    if exhibited_on is None:
                        return datetime.datetime(1900, 1, 1)  # A default date for records with null exhibited_on
                    return datetime.datetime.strptime(exhibited_on, "%B %Y")

                # Separate the records with "N/A" from others
                records_with_na = [record for record in achievements_and_accolades if record.get('exhibited_on') == "N/A"]
                records_without_na = [record for record in achievements_and_accolades if record.get('exhibited_on') != "N/A"]

                # Sort the records without "N/A"
                sorted_records_without_na = sorted(records_without_na, key=get_exhibited_on, reverse=True)

                # Combine the sorted records and records with "N/A"
                sorted_achievements_and_accolades = sorted_records_without_na + records_with_na

                for record in sorted_achievements_and_accolades:
                    # Remove 'updated_at' and 'created_at' keys
                    record.pop("updated_at", None)
                    record.pop("created_at", None)

                
                return Response({"achievements_and_accolades": sorted_achievements_and_accolades})
            else:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, pk):
        try:
                # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            if not profile:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)
                
                
            achievements_and_accolades = profile.get("achievements_and_accolades", [])

            if achievements_and_accolades is None:
                achievements_and_accolades = []

            max_id = max([ach.get('id', 0) for ach in achievements_and_accolades], default=0)

            # Increment the maximum ID to generate a unique ID for the new achievement
            unique_id = max_id + 1
                
            new_achievements_and_accolades = {
                    "id": unique_id,
                    **request.data.get("achievements_and_accolades"),
                    "updated_at": datetime.datetime.now(),
                    "created_at": datetime.datetime.now(),
                    "retrieved_from": "user"
                }

            achievements_and_accolades.append(new_achievements_and_accolades)
                
            profile["achievements_and_accolades"] = achievements_and_accolades
                
            profile["updated_at"] = datetime.datetime.now()
                
            resume_data.update_one({'user_id': str(pk)}, {'$set': profile})

            return Response({"message": "Successfully Added"})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, pk, ach_id):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            if not profile:
                return Response({"message": "Profile not found"}, status=status.HTTP_400_BAD_REQUEST)

            # Get the "achievements_and_accolades" array from the profile document
            achievements_and_accolades = profile.get("achievements_and_accolades", [])

            # Find the "achievements_and_accolades" document with the given ID
            updated_achievements_and_accolades = None
            for ach in achievements_and_accolades:
                if ach.get("id") == int(ach_id):
                    updated_achievements_and_accolades = ach
                    break

            if updated_achievements_and_accolades:
                # Update the fields of the "achievements_and_accolades" document with the provided data
                updated_achievements_and_accolades_data = request.data.get("updated_achievements_and_accolades")
                if updated_achievements_and_accolades_data:
                    updated_achievements_and_accolades.update(updated_achievements_and_accolades_data)
                    updated_achievements_and_accolades["updated_at"]=datetime.datetime.now()

                    # Update the "updated_at" field in the profile document
                    profile["updated_at"] = datetime.datetime.now()

                    # Update the entire profile document in the database
                    resume_data.update_one({'user_id': str(pk)}, {'$set': profile})

                    return Response({"message": "Successfully Updated"})
                else:
                    return Response({"message": "No data provided for update"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"message": "achievements_and_accolades not found"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, pk, achievement_id):
        try:
            # Retrieve the profile document
            profile = resume_data.find_one({'user_id': str(pk)})
            if profile is None:
                return Response({"message": "No User Found"}, status=status.HTTP_400_BAD_REQUEST)
            
            achievements_and_accolades = profile.get('achievements_and_accolades', [])

            achievement_id = int(achievement_id)

            
            found = False
            updated_achievements = []

            for ach in achievements_and_accolades:
                if ach.get('id') == achievement_id:
                    found = True
                else:
                    updated_achievements.append(ach)

            if not found:
                return Response({"message": "Achievement not found"}, status=status.HTTP_400_BAD_REQUEST)

            # Update the profile document with the modified achievements_and_accolades list
            profile['achievements_and_accolades'] = updated_achievements
            resume_data.update_one({'user_id': str(pk)}, {'$set': profile})

            return Response({"message": "Achievement deleted successfully"})
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class GetBasicDetails(APIView):

    def get(self, request):
      #  try:
            user_id = request.query_params.get("id")
            if not user_id:
                return Response({"message": "id not provided"}, status=status.HTTP_400_BAD_REQUEST)

            # Retrieve user data by user_id from MongoDB
            user_object_id = ObjectId(user_id)
            # print(user_object_id)

            # Retrieve user data by user_id from MongoDB
            user_data = users_registration.find_one({"_id": user_object_id})
            # print(user_data)
            #print(f"Retrieved user data: {user_data}")

            #user_data = collection.find_one({"_id": user_id})
            profile_object_id = (user_id)
            # print(profile_object_id)

            profile_data = resume_data.find_one({"user_id": profile_object_id})
            # print(f"Retrieved profile data: {profile_data}")
            current_role = ""
            current_company = ""
            current_experience = ""
           
            # Find the experience with an end_date of "Present"
            experiences = profile_data.get("experience", [])
            # print(experiences)
            for experience in experiences:
                if "end_date" in experience and experience["end_date"] == "Present":
                    current_role = experience.get("role", "")
                    current_company = experience.get("company", "")
                    current_experience = calculate_experience_duration(experience.get("start_date", ""), "present")
                    #current_experience = calculate_experience_duration(experience.get("start_date", ""))
                    # print(current_role)
                    # print(current_company)
                    break  # Stop after finding the first valid experience
            # if current_role  and current_company is None:
            #     return Response({"message": "No valid experience found"}, status=status.HTTP_400_BAD_REQUEST)
            

            if user_data and profile_data:
                city = profile_data.get("city")
                country = profile_data.get("country")
                if not city and not country:
                    location = None
                elif not city:
                    location = f"{country}"
                elif not country:
                    location = f"{city}"
                else:
                    location = f"{city}, {country}"
                response_data = {
                    "first_name" : user_data.get("first_name"),
                    "last_name" : user_data.get("last_name"),
                    "profile_image" : user_data.get("profile_image"),
                    "location" : location,
                    "email": user_data.get("email"),
                    "current_role": current_role,
                    "current_company" : current_company,
                    "current_experience" : current_experience

                }
                # print(response_data)
                # created_at = datetime.strptime(user_data.get("created_at"), "%d-%m-%y %H:%M:%S")
                # current_date = datetime.now()
                # time_difference = relativedelta(current_date, created_at)
                # time_since_creation = f"{time_difference.years} years, {time_difference.months} months"
                # response_data["member_since"] = time_since_creation
                created_at = user_data.get("created_on")
                current_date = datetime.datetime.now()
                time_difference = relativedelta(current_date, created_at)
                   
                years = time_difference.years
                months = time_difference.months
                days = time_difference.days

                time_since_creation = ""
                if years > 0:
                    if months >= 12:
                        time_since_creation += f"{years + 1} year{'s' if years + 1 != 1 else ''}"
                    else:
                        time_since_creation += f"{years} year{'s' if years != 1 else ''}"

                    if months > 0:
                        time_since_creation += f" {months} month{'s' if months != 1 else ''}"
                elif months > 0:
                    time_since_creation += f"{months} month{'s' if months != 1 else ''}"
                else:
                    days = time_difference.days
                    time_since_creation += f"{days} day{'s' if days != 1 else ''}"

                response_data["member_since"] = time_since_creation
                   
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response({"message": "User not found"}, status=status.HTTP_400_BAD_REQUEST)

        # except Exception as e:
        #     return Response({"message": "An error occurred","error":str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserUpdate(APIView):
    def patch(self, request):
        try:
            user_id = request.query_params.get("id")
            if not user_id:
                return Response({"message": "User ID not provided"}, status=status.HTTP_400_BAD_REQUEST)
            updated_data = {}

            # Update only if first_name is provided
            if "first_name" in request.data:
                updated_data["first_name"] = request.data["first_name"]

            # Update only if last_name is provided
            if "last_name" in request.data:
                updated_data["last_name"] = request.data["last_name"]
            # Convert user_id to ObjectId
            user_object_id = ObjectId(user_id)
            

            # Update the user data
            users_registration.update_one({"_id": user_object_id}, {"$set": updated_data})

            return JsonResponse({"message": "User data updated successfully"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

class Update_communication_preferences(APIView):
    def patch(self, request):
        try:
            user_id = request.query_params.get("id")
            if not user_id:
                return Response({"message": "User ID not provided"}, status=status.HTTP_400_BAD_REQUEST)
            updated_data = request.data  # Fields to update

            # Convert user_id to ObjectId
            user_object_id = ObjectId(user_id)

            # Prepare the update query
            update_query = {"$set": {}}

            if "account_notifications" in updated_data:
                update_query["$set"]["communication_preferences.account_notifications"] = updated_data["account_notifications"]
            
            if "product_updates" in updated_data:
                update_query["$set"]["communication_preferences.product_updates"] = updated_data["product_updates"]
            
            if "newsletter" in updated_data:
                update_query["$set"]["communication_preferences.newsletter"] = updated_data["newsletter"]

            users_registration.update_one({"_id": user_object_id}, update_query)

            return JsonResponse({"message": "User data updated successfully"}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

class Update_account_integrations(APIView):
    def patch(self, request):
        try:
            user_id = request.query_params.get("id")
            if not user_id:
                return Response({"message": "User ID not provided"}, status=status.HTTP_400_BAD_REQUEST)
            updated_data = request.data  # Fields to update

            # Convert user_id to ObjectId
            user_object_id = ObjectId(user_id)

            # Prepare the update query
            update_query = {"$set": {}}

            if "linkedin" in updated_data:
                update_query["$set"]["account_integrations.linkedin"] = updated_data["linkedin"]
            
            if "Naukri" in updated_data:
                update_query["$set"]["account_integrations.Naukri"] = updated_data["Naukri"]

            users_registration.update_one({"_id": user_object_id}, update_query)

            return JsonResponse({"message": "User data updated successfully"}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

class GetAccountSettings(APIView):
    def get(self, request):
        try:
            user_id = request.query_params.get("id")
            if not user_id:
                return Response({"message": "User ID not provided"}, status=status.HTTP_400_BAD_REQUEST)

            # Convert user_id to ObjectId
            user_object_id = ObjectId(user_id)
           
            user_data = users_registration.find_one({"_id": user_object_id})

            if user_data:
                # Extract the desired fields from user_data
                response_data = {
                    "first_name": user_data.get("first_name"),
                    "last_name": user_data.get("last_name"),
                    "email": user_data.get("email"),
                    "password" : user_data.get("password"),
                    "country_code": user_data.get("country_code"),
                    "phone_number": user_data.get("phone_number"),
                    "2fa": user_data.get("2fa"),
                    "profile_image" : user_data.get("profile_image"),
                    "account_integrations":user_data.get("account_integrations"),
                    "communication_preferences":user_data.get("communication_preferences")

                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response({"message": "User not found"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"message": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetUserName(APIView):
    def get(self, request):
        try:
            user_id = request.query_params.get("id")
            if not user_id:
                return Response({"message": "User id not provided"}, status=status.HTTP_400_BAD_REQUEST)
            # Convert user_id to ObjectId
            user_object_id = ObjectId(user_id)
            user_data = users_registration.find_one({"_id": user_object_id})

            if user_data:
                # Extract the desired fields from user_data
                response_data = {
                    "first_name": user_data.get("first_name"),
                    "last_name": user_data.get("last_name"),
                    "profile_image" : user_data.get("profile_image")
                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response({"message": "User not found"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"message": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 

#forgot password/reset password
class request_new_password_view(APIView):
    def post(self, request):
        request_data=request.body
        data=json.loads(request_data)
        email_id=data['email']
        user = users_registration.find_one({'email': email_id})
        if user:
            user_object_id = str(user["_id"])
            print("object id:",user_object_id)
            uid = urlsafe_base64_encode(force_bytes(user_object_id))
            print("uid:",uid)
            print('**********')
            import uuid
            token= str(uuid.uuid4())
            print("token:",token)
            expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=5)
            users_registration.update_one({"_id": user["_id"]}, {"$set": {"password_reset_token": token, "password_reset_expiry_time": expiry_time}})
            print('Password Reset Token', token)
            link = f'{base_url}/reset-password/'+uid+'/'+token
            print('Password Reset Link', link)
            # Send EMail
            subject = "Project Momentum – Setup New Password"
            content = f'''Dear User,<br><br>

            We've received a request to reset the password for your 'Youe' account</b><br>


            Click on the link below to set a new password:<br>
            {link}<br><br><br>

            Regards,<br>
            Team – Project Momentum'''

            send_emails(subject, email_id, content)
            return Response({'message':'Your password reset link has been successfully sent to your email address.Please check your email for further instructions.'}, status=status.HTTP_200_OK)
        return Response({'message':'The account does not exist'}, status=status.HTTP_400_BAD_REQUEST)


class setup_newpassword_view(APIView):
    def post(self, request, uid, token, format=None):
        request_data=request.body
        data=json.loads(request_data)
        try:
            request_id = smart_str(urlsafe_base64_decode(uid))
            try:
                user = users_registration.find_one({'_id': ObjectId(request_id)})
            except bson.errors.InvalidId:
                return Response({'message':'user not found'}, status=status.HTTP_400_BAD_REQUEST)
            if not user:
                return Response({'message':'Invalid password reset link'}, status=status.HTTP_400_BAD_REQUEST)
            # user_object_id = str(user["_id"])
            request_token = users_registration.find_one({"password_reset_token": token})
            if not request_token:
                return Response({'message':'Invalid password reset link'}, status=status.HTTP_400_BAD_REQUEST)

            if datetime.datetime.now() > user["password_reset_expiry_time"]:
                return Response({'message':'Password reset link has expired.'}, status=status.HTTP_400_BAD_REQUEST)

            new_password = data.get("password")
            if not new_password:
                return Response({'message':'Please provide a password.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Hash the password
            hashed_password = make_password(new_password)
            users_registration.update_one({"_id": user["_id"]}, {"$set": {"password": hashed_password,"updated_at":datetime.datetime.now()}})
            users_registration.update_one({"_id": user["_id"]}, {"$unset": {"password_reset_token": "", "password_reset_expiry_time": ""}})

            return Response({'message':'Password successfully changed!'}, status=status.HTTP_200_OK)
            
        except DjangoUnicodeDecodeError:
            #PasswordResetTokenGenerator().check_token(user, token)
            return Response({"message":"The link is not Valid or Expired"},status=status.HTTP_400_BAD_REQUEST)
    
class CheckPasswordResetLink(APIView):
    def get(self, request, uid, token, format=None):
        try:
            request_id = smart_str(urlsafe_base64_decode(uid))
            print(request_id)
            try:
                user = users_registration.find_one({'_id': ObjectId(request_id)})
            except bson.errors.InvalidId:
                return Response({'message': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)

            if not user:
                return Response({'message': 'Invalid password reset link'}, status=status.HTTP_400_BAD_REQUEST)

            request_token = users_registration.find_one({"password_reset_token": token})
            if not request_token:
                return Response({'message': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


            if datetime.datetime.now() > user["password_reset_expiry_time"]:
                users_registration.update_one({'_id': user["_id"]}, {"$unset": {"password_reset_token": "", "password_reset_expiry_time": ""}})
                return Response({'message': 'The password reset link has expired. Please initiate the password reset process again.'}, status=status.HTTP_400_BAD_REQUEST)

            return Response({'message': 'Password reset link is valid'}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class PhoneCodes(APIView):
    def get(self, request):
        query = request.GET.get('q')
        
        if query:
            
            try:
                pipeline = []
                match_criteria = {
                    '$or': [
                        {'name': {'$regex': '^' + query, '$options': 'i'}}
                    ]
                }
                pipeline.append({
                    '$match': match_criteria
                })
                results = list(phone_codes.aggregate(pipeline))
                extracted_data = []
                for result in results:
                    extracted_data.append({
                        "name": result.get("name"),
                        "dial_code" : result.get("dial_code"),
                        "flag": result.get("flag")
                    })
                return Response({"result": extracted_data}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"message": "An error occurred", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
           
            try:
                phone_codess = phone_codes.find({})
                code_list = [code for code in phone_codess]
                extracted_data = []
                for code in code_list:
                    extracted_data.append({
                        "name": code.get("name"),
                        "dial_code" : code.get("dial_code"),
                        "flag": code.get("flag")
                    })
                return Response({"result": extracted_data}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"message": "An error occurred", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

import pymongo
class Industry(APIView):
    def get(self, request):
        query = request.GET.get('q')
        if query:
            return self.get_industry_options(query)
        else:
            return self.get_all_industries()

    def get_industry_options(self, selected_industry):
        # try:
            industry.create_index([("industry", pymongo.ASCENDING)])
            existing_indexes = industry.index_information()

            # Print the existing indexes
            # print("Existing Indexes:", existing_indexes)
            indust = industry.find_one({"industry": selected_industry})
            if indust:
                data = {
                    "company_type": [item["name"] for item in indust.get('company_type', [])],
                    "functions": [item["name"] for item in indust.get('function', [])],
                }
                # return Response({"result": data}, status=status.HTTP_200_OK)
                return Response({'result': data}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "Industry not found"}, status=status.HTTP_400_BAD_REQUEST)
        # except Exception as e:
        #     return Response({"message": "An error occurred", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_all_industries(self):
        # try:
            industries = industry.distinct("industry")  # Retrieve all distinct industry names
            return Response({"result": industries}, status=status.HTTP_200_OK)
        # except Exception as e:
            # return Response({"message": "An error occurred", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class Function(APIView):
    def get(self, request):
        query = request.GET.get('q')
        if query:
            return self.get_function_options(query)
        else:
            return self.get_all_function()

    def get_function_options(self, selected_function):
        try:
            indust = function.find_one({"function": selected_function})
            if indust:
                data = {
                    "domains": [item["name"] for item in indust.get('domain', [])],
                    "rank": [item["name"] for item in indust.get('rank', [])],
                }
                
                # return Response({"result": data}, status=status.HTTP_200_OK)
                return Response({"result": data}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "function not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_all_function(self):
        try:
            industries = function.distinct("function")  # Retrieve all distinct industry names
            return Response({"result": industries}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": "An error occurred", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    @csrf_exempt
    def patch(self, request, selected_industry, company_type_id):
        new_company_type_name = request.data.get('new_company_type_name')

        try:
           
            # Find the document for the selected industry
            indus = industry.find_one({"industry": selected_industry})

            if indus:
                # Update the company type option with the specified ID
                for company_type in indus['company_type']:
                    if company_type['id'] == company_type_id:
                        company_type['name'] = new_company_type_name

                # Update the document in MongoDB
                update_result = collection.update_one(
                    {"_id": indus['_id'], "company_type.id": company_type_id},
                    {"$set": {"company_type.$.name": new_company_type_name}}
                )

                return Response({"message": "Company type updated successfully"}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "Industry not found"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"message": "An error occurred", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class Career_Stream(APIView):
    def get(self, request):
        try:
            domain = function.distinct("domain") 
            if domain:
                domain_names = [item["name"] for item in domain]
                return Response({"result": domain_names}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "Stream not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)