from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from users.mongoDb_connection import users_registration,resume_data
from linkedin.utils import linkedin_signin_openid,linkedin_url
from youe_backend import settings
from rest_framework.request import Request
from bson import ObjectId
from linkedin.validate import validate_achievements,validate_certifications,validate_education,validate_experience
import datetime
from users.utils import calculate_redirect_step,onboarding_status_fun
from youe_backend.settings import base_url
import requests
import os
import json
from linkedin.chatgpt import tech_skill_mapping


from django.shortcuts import redirect

from urllib.parse import urlencode



'''
Linkedin Credentials
'''
# API requirements
CLIENT_ID = settings.LINKEDIN_CLIENT_ID
CLIENT_SECRETE = settings.LINKEDIN_CLIENT_SECRET
PROXY_CURL_API_KEY=settings.PROXY_CURL_API_KEY
AUTHORIZATION_URL = 'https://www.linkedin.com/oauth/v2/authorization/'
TOKEN_URL = 'https://www.linkedin.com/oauth/v2/accessToken/'
PROXY_CURL_API_URL = 'https://nubela.co/proxycurl/api/v2/linkedin'
LINKEDIN_SCOPES = ['openid', 'profile', 'email','r_basicprofile']



# Create your views here

'''Linkedin Token'''
class LinkedinAuthorizationUrl(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        # check if the code is present in the request body
        code = request.GET.get('code')
        type_param = request.GET.get('type')

        if not code:
            if type_param == 'signin':

                signup_redirect_URI = f'{base_url}/linkedin-signin/success'

                params = {
                'response_type': 'code',
                'client_id': CLIENT_ID,
                'redirect_uri': signup_redirect_URI,
                'state': 'some-random-state',
                'scope': ' '.join(LINKEDIN_SCOPES)  # Use space-separated scopes
                }
                # print('redirect_uri', signup_redirect_URI)
                authorization_url = f"{AUTHORIZATION_URL}?{urlencode(params)}"
                return Response({'authorization_url': authorization_url}, status=status.HTTP_200_OK)

            elif type_param == 'signup':
                # print('base',base_url)
                # signup_redirect_URI = f'{base_url}/linkedin-signup/success'
                signup_redirect_URI = 'http://localhost:3000/linkedin-signup/success'
                
                params = {
                'response_type': 'code',
                'client_id': CLIENT_ID,
                'redirect_uri': signup_redirect_URI,
                'state': 'some-random-state',
                'scope': ' '.join(LINKEDIN_SCOPES)  # Use space-separated scopes
                }   
                # print('redirect_uri', signup_redirect_URI)
                
                authorization_url = f"{AUTHORIZATION_URL}?{urlencode(params)}"

                return Response({'authorization_url': authorization_url}, status=status.HTTP_200_OK)
            else:
                # Handle the case when 'type' is not 'signin' or 'signup'
                return Response({'error': 'Invalid type value'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # If the 'code' is present, return it as a JSON response
            return Response({'code': code}, status=status.HTTP_200_OK)


# class LinkedinRetriev(APIView):
    
#         def get(self, request,id):
#             try:
                
#                 user=users_registration.find_one({"_id":ObjectId(id)})
#                 if user is None:
#                     return Response({"message":"User Not Found"},status=status.HTTP_400_BAD_REQUEST)
#                 user_id=ObjectId(id)
#                 print(user_id)
#                 linkedin_url = user.get('linkedin_public_url')
#                 linkedin_profile_url = linkedin_url
#                 api_key = PROXY_CURL_API_KEY
#                 headers = {'Authorization': 'Bearer ' + api_key}

#                 response = requests.get(PROXY_CURL_API_URL,
#                                         params={'url': linkedin_profile_url,'skills': 'include'},
#                                         headers=headers)
#                 data = response.json()
                
                
#                 if data.get('code') == 403:
#                     return Response({"message": "Rate limit exceeded. Please try again later."}, status=status.HTTP_403_FORBIDDEN)
                
#                 if data.get('code') == 400:
#                     return Response({"message": "Rate limit exceeded. Please try again later."}, status=status.HTTP_400_BAD_REQUEST)
                
#                 if data.get('code') == 401:
#                     return Response({"message": "Invalid API Key"}, status=status.HTTP_401_UNAUTHORIZED)
                
#                 if data.get('code') == 429:
#                     return Response({"message": "Rate limited. Please retry"}, status=status.HTTP_429_TOO_MANY_REQUESTS)

#                 # print(data)
#                 # print(data.keys())


#                 city = data["city"]
#                 country = data["country_full_name"]
#                 # print(country)
#                 current_role = data["occupation"]
#                 education_levels = data["education"]
#                 education_levels = validate_education(education_levels)

#                 work_experience = data["experiences"]
#                 work_experience = validate_experience(work_experience)

#                 certifications = data["certifications"]
#                 certifications = validate_certifications(certifications)

#                 achievements = data["accomplishment_honors_awards"]
#                 achievements = validate_achievements(achievements)

#                 technical_skills = data["skills"]

#                 overall_experience = tech_skill_mapping(work_experience, technical_skills)

#                 restructured_data = {
#                         "user_id": str(user_id),
#                         "current_occupation":current_role,
#                         "city" : city,
#                         "country" : country,
#                         "education":education_levels,
#                         "experience":json.loads(overall_experience),
#                         "certifications_and_courses":certifications,
#                         "achievements_and_accolades":achievements,
#                         "updated_at":datetime.datetime.now(),
#                         "created_at":datetime.datetime.now()

#                     }
#                 profile_id = resume_data.insert_one(restructured_data)
#                 restructured_data.pop('_id')
#                 # users_registration.update_one({'_id': ObjectId(user_id)}, {'$set': {"onboarding_process":{"step":5,"process":"Linkedin"}}})
                
#                 return Response({"message":"resume upload sucessfully","resume_response":restructured_data},status=status.HTTP_200_OK)
#             except json.JSONDecodeError:
#                 return Response({"message":"Please upload the resume again"},status=status.HTTP_400_BAD_REQUEST)
            
#             except Exception as e:
#                     # Log the exception for debugging
#                 return Response({"message": "An error occurred", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         def post(self, request):
#             try:
#                 data=request.data
#                 user_id=data.get("user_id")
#                 linkedin_url = data.get("linkedin_url")
#                 user=users_registration.find_one({"_id":ObjectId(user_id)})
#                 if user is None:
#                     return Response({"message":"User Not Found"},status=status.HTTP_400_BAD_REQUEST)
#                 linkedin_profile_url = linkedin_url
#                 api_key = PROXY_CURL_API_KEY
#                 headers = {'Authorization': 'Bearer ' + api_key}

#                 response = requests.get(PROXY_CURL_API_URL,
#                                         params={'url': linkedin_profile_url,'skills': 'include'},
#                                         headers=headers)
#                 data = response.json()
#                 if data.get('code') == 403:
#                     return Response({"message": "Rate limit exceeded. Please try again later."}, status=status.HTTP_403_FORBIDDEN)

#                 if data.get('code') == 400:
#                     return Response({"message": "Rate limit exceeded. Please try again later."}, status=status.HTTP_400_BAD_REQUEST)
                
#                 if data.get('code') == 401:
#                     return Response({"message": "Invalid API Key"}, status=status.HTTP_401_UNAUTHORIZED)
                
#                 if data.get('code') == 429:
#                     return Response({"message": "Rate limited. Please retry"}, status=status.HTTP_429_TOO_MANY_REQUESTS)

#                 print(data)

#                 city = data["city"]
#                 country = data["country_full_name"]
#                 current_role = data["occupation"]
#                 education_levels = data["education"]
#                 education_levels = validate_education(education_levels)

#                 work_experience = data["experiences"]
#                 work_experience = validate_experience(work_experience)

#                 certifications = data["certifications"]
#                 certifications = validate_certifications(certifications)

#                 achievements = data["accomplishment_honors_awards"]
#                 achievements = validate_achievements(achievements)

#                 technical_skills = data["skills"]


#                 restructured_data = {
#                         "user_id": user_id,
#                         "current_occupation":current_role,
#                         "city" : city,
#                         "country" : country,
#                         "education":education_levels,
#                         "experience":work_experience,
#                         "certifications_and_courses":certifications,
#                         "achievements_and_accolades":achievements,
#                         "updated_at":datetime.datetime.now(),
#                         "created_at":datetime.datetime.now()

#                     }
#                 profile_id = resume_data.insert_one(restructured_data)
#                 restructured_data.pop('_id')
#                 users_registration.update_one({'_id': ObjectId(user_id)}, {'$set': {"onboarding_process":{"step":5,"process":"Linkedin"}}})
#                 return Response({"message":"resume upload sucessfully","profile_id":str(profile_id.inserted_id),"resume_response":restructured_data},status=status.HTTP_200_OK)
#             except Exception as e:
#                     # Log the exception for debugging
#                 return Response({"message": "An error occurred", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

 
class LinkedinSignUpAPI(APIView):

    def post(self, request):
        # try:
        # Get the 'code' from the request body
            code = request.data.get('code')

            if not code:
                return Response({'message': 'Authorization code is missing in the request body.'}, status=status.HTTP_400_BAD_REQUEST)

            profile_data_response = linkedin_signin_openid(request,code,"signup")

            if not profile_data_response:
                return Response({'message': 'Failed to fetch user profile from LinkedIn.'}, status=status.HTTP_400_BAD_REQUEST)
            # print("profile_data_response: ",profile_data_response)

            if 'email' not in profile_data_response:
                return Response({'message': 'Oops! Something went wrong on our end while fetching data from LinkedIn. Please try again.'},status=status.HTTP_400_BAD_REQUEST)
            
            vanity_name= profile_data_response["vanity_name"]
            # print("profile_data_response: ",profile_data_response)
            user = users_registration.find_one({'email': profile_data_response['email']})
            if user:
                user_id = user['_id']
                onboarding_process = user.get("onboarding_process")
                if onboarding_process is None:
                    return Response({"message": "Onboarding process information not found"}, status=status.HTTP_400_BAD_REQUEST)

                onboarding_status = onboarding_process.get("step")
                onboarding_step= onboarding_status_fun(onboarding_status)
                redirect_step = calculate_redirect_step(user, onboarding_status)
                if onboarding_status == 8:
                    return Response(
                        {
                            'message': 'User already exists, Please logout of the LinkedIn once and try again. If you are  a registered member, Please click on Sign in.',
                            "user_id":str(user_id),
                            "onboarding_status":onboarding_step}, 
                            status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response(
                        {
                            'message': 'Please complete the on-boarding process',
                            "user_id":str(user_id),
                            "redirect_step":redirect_step,
                            "onboarding_status":onboarding_step}, 
                            status=status.HTTP_200_OK)
                # Create a new user with the profile data
            new_user = {
                "email_verified": profile_data_response["email_verified"],
                "email": profile_data_response["email"],
                "first_name": profile_data_response["given_name"],
                "last_name": profile_data_response["family_name"],
                "linkedin_public_url": f'https://www.linkedin.com/in/{vanity_name}/',
                "signup_type":"Linkedin",
                "2fa":False,
                "updated_at": datetime.datetime.now(),
                "last_login": datetime.datetime.now(),
                "created_on": datetime.datetime.now(),
                "onboarding_process":{"step":0,"process":"Linkedin Signup"}
                }
            user_id = users_registration.insert_one(new_user).inserted_id
            # request = Request(request)
            # linkedin_retriev_instance = LinkedinRetriev()

            # Call the get method of the LinkedinRetriev class with the user_id
            responsereere = linkedin_url(request, user_id)
            print("ablalala: " , responsereere)
            return Response(
                {
                "message": "Successfully registered", 
                "user_id": str(user_id), 
                "first_name":profile_data_response["given_name"],
                "last_name":profile_data_response["family_name"]
                },
                status=status.HTTP_200_OK)
        # except Exception as e:
        #     return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LinkedinSigninAPI(APIView):
    def post(self, request):
        try:
            # Get the 'code' from the request body
            code = request.data.get('code')

            if not code:
                return Response({'message': 'Authorization code is missing in the request body.'}, status=status.HTTP_400_BAD_REQUEST)

            # Call the LinkedIn Signin OpenID API to exchange the code for user profile data
            profile_data_response = linkedin_signin_openid(request,code,"signin")

            if not profile_data_response:
                return Response({'message': 'Failed to fetch user profile from LinkedIn.'}, status=status.HTTP_400_BAD_REQUEST)

            if 'email' not in profile_data_response:
                return Response({'message': 'Oops! Something went wrong on our end while fetching data from LinkedIn. Please try again.'}, status=status.HTTP_400_BAD_REQUEST)

            user = users_registration.find_one({'email': profile_data_response['email']})

            if not user:
                return Response({'message': 'Email does not exist.',"onboarding_status": 0}, status=status.HTTP_400_BAD_REQUEST)

            user_id = user['_id']
            onboarding_process = user.get("onboarding_process")

            if onboarding_process is None:
                return Response({"message": "Onboarding process information not found"}, status=status.HTTP_400_BAD_REQUEST)

            onboarding_status = onboarding_process.get("step")

            if onboarding_status is None:
                return Response(
                    {"message": "Please complete the onboarding process", "user_id": str(user_id),"redirect_step": onboarding_status+1,"onboarding_status":1},
                    status=status.HTTP_200_OK,
                )
            onboarding_step= onboarding_status_fun(onboarding_status)
            redirect_step = calculate_redirect_step(user, onboarding_status)
            if onboarding_status != 8:
                return Response(
                    {
                        "message": "Please complete the onboarding process",
                        "user_id": str(user_id),
                        "onboarding_status": onboarding_step,
                        "redirect_step": redirect_step
                    },
                    status=status.HTTP_200_OK,
                )
            users_registration.update_one({'_id': ObjectId(user_id)}, {'$set': {'last_login': datetime.datetime.now()}})
            return Response(
                {
                    "message": "Successfully logged in", 
                    "user_id": str(user_id),
                    "onboarding_status": onboarding_step}, 
                    status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": "An error occurred", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


