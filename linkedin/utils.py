from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from users.mongoDb_connection import users_registration,resume_data
from youe_backend import settings
from youe_backend.settings import base_url
from linkedin.validate import validate_achievements,validate_certifications,validate_education,validate_experience
import requests
import os
from django.shortcuts import redirect
import json
from bson import ObjectId
from urllib.parse import urlencode
from linkedin.chatgpt import tech_skill_mapping


'''
Linkedin Credentials
'''

# API requirements
CLIENT_ID = settings.LINKEDIN_CLIENT_ID
CLIENT_SECRETE = settings.LINKEDIN_CLIENT_SECRET
TOKEN_URL = 'https://www.linkedin.com/oauth/v2/accessToken/'
USERINFO_URL_1 = 'https://api.linkedin.com/v2/userinfo'
USERINFO_URL = 'https://api.linkedin.com/v2/me'






def linkedin_signin_openid(request,code,type):

        authentication_classes = []
        permission_classes = [AllowAny]
        # Check if the 'code' parameter is present in the query string
        # code = request.GET.get('code')
        code = code
        if not code:
            return Response({'error': 'Authorization code is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        if type == 'signin':
            
            REDIRECT_URI_1 = f'{base_url}/linkedin-signin/success'

        else:
            
            # REDIRECT_URI_1 = f'{base_url}/linkedin-signup/success'
            REDIRECT_URI_1 = 'http://localhost:3000/linkedin-signup/success'
            

        # Exchange the authorization code for an access token
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI_1,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRETE,
        }

        # print("REDIRECT_URI_1: " , REDIRECT_URI_1)
        # print('data', data)

        response = requests.post(TOKEN_URL, data=data)
        # print('Token exchange response:', response.content)
        if response.status_code != 200:
            return Response({'error': 'Failed to exchange authorization code for access token.'}, status=status.HTTP_400_BAD_REQUEST)

        token_data = response.json()
        access_token = token_data.get('access_token')

        if not access_token:
            return Response({'error': 'Access token not found in response.'}, status=status.HTTP_400_BAD_REQUEST)

        # Use the access token to fetch the user's profile information
        headers = {'Authorization': f'Bearer {access_token}'}
        response_1 = requests.get(USERINFO_URL, headers=headers)
        response_2 = requests.get(USERINFO_URL_1, headers=headers)

        if response_1.status_code != 200 and response_2.status_code !=200 :
            return Response({'error': 'Failed to fetch user profile.'}, status=status.HTTP_400_BAD_REQUEST)

        user_info_1 = {'vanity_name': response_1.json().get('vanityName')}
        user_info_2 = response_2.json()
        user_info = {**user_info_1, **user_info_2}
        # At this point, you have the user's LinkedIn profile data in profile_data.
        # You can create or authenticate the user in your Django application as needed.
        print("profile_data",user_info)
        return user_info


    
def linkedin_url(request,user_id):
            # try:
                
                user=users_registration.find_one({"_id":ObjectId(user_id)})
                if user is None:
                    return Response({"message":"User Not Found"},status=status.HTTP_400_BAD_REQUEST)
                user_id=ObjectId(user_id)
                print(user_id)
                # linkedin_url = user.get('linkedin_public_url')
                # linkedin_profile_url = linkedin_url
                # api_key = PROXY_CURL_API_KEY
                # headers = {'Authorization': 'Bearer ' + api_key}

                # response = requests.get(PROXY_CURL_API_URL,
                #                         params={'url': linkedin_profile_url,'skills': 'include'},
                #                         headers=headers)
                # data = response.json()
                data = {
                    "public_identifier": "sandhyamishra25",
                    "profile_pic_url": "https://media.licdn.com/dms/image/D4E03AQFnUQ7LKBLTgA/profile-displayphoto-shrink_400_400/0/1694701302543?e=1713398400&v=beta&t=UzqKrfmSCUDTM-9PY-CKMIH-BW1kia32XHigp9P5OYI",
                    "background_cover_image_url": "https://media.licdn.com/dms/image/C4D16AQEa4rP1-a5u4w/profile-displaybackgroundimage-shrink_200_800/0/1648972548268?e=1713398400&v=beta&t=I-DvHEke4iIdnaAcoY6HhGO2sKu4kVNrz20OkuSdsIw",
                    "first_name": "Sandhya ",
                    "last_name": "Mishra",
                    "full_name": "Sandhya  Mishra",
                    "follower_count": 85836,
                    "occupation": "Consultant at Personal.ai",
                    "headline": "AI Consultant | AI Enthusiast | Programmer | Content Creator | Prompt Engineer | Helping brands to grow | Multitasker",
                    "summary": "Hello everyone! I'm Sandhya, a diligent and multitasking individual who thrives in leadership roles. Currently pursuing my undergraduate degree in Computer Science at VIT, Jaipur, I am driven by a strong work ethic and a passion for continuous learning. 💪💼\n\nWith a firm grasp of programming fundamentals, particularly in C/C++, data structures, and competitive programming, I am adept at solving complex problems and approaching challenges with a logical mindset. 🖥️\n\nAdditionally, I possess extensive experience as a full-stack MERN developer, crafting dynamic web applications that offer seamless user experiences. From designing captivating user interfaces to developing robust back-end systems, I strive for excellence in all aspects of the development process. 💻\n\nAs the founder of Hustlers Sunshine, a vibrant community with over 6000 active members on our WhatsApp group, I have honed my leadership skills and fostered an environment where individuals can share valuable resources, receive guidance, and explore job opportunities. It is a testament to my ability to bring people together and facilitate growth. 🌞✨\n\nIf you're looking to enhance your LinkedIn presence, I am confident that I can help you achieve your goals. With my expertise in social media management, I offer personalized strategies and invaluable tips to help you stand out, establish a strong brand identity, and forge meaningful connections.✅ I am dedicated to assisting you in growing your brand and optimizing your LinkedIn profile.\n\nIf you're interested in collaborating on exciting projects or exploring partnership opportunities, I am always open to new ventures. Feel free to reach out to me at mishrasandhya25sm2003@gmail.com, and let's connect to discuss how we can collaborate and create something extraordinary together!\n\nPlease don't hesitate to contact me. I look forward to connecting with you and exploring possibilities for collaboration.\nPortfolio website: https://sandhyamishra18.github.io/SANDHYA-PORTFOLIO.github.io/",
                    "country": "IN",
                    "country_full_name": "India",
                    "city": "Jaipur",
                    "state": "Rajasthan",
                    "experiences": [
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 10,
                            "year": 2023
                        },
                        "ends_at": None,
                        "company": "Personal.ai",
                        "company_linkedin_profile_url": "https://www.linkedin.com/company/personalai",
                        "title": "Consultant",
                        "description": None,
                        "location": "Newyork  · Remote",
                        "logo_url": "https://media.licdn.com/dms/image/D560BAQEVYgMwajW_zw/company-logo_400_400/0/1697411984846/personalai_logo?e=1715817600&v=beta&t=C7WL0uw-HqUryADchxNAlfBPG6oEFIU2YCAjCe7funw"
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 5,
                            "year": 2022
                        },
                        "ends_at": None,
                        "company": "Codess.Cafe",
                        "company_linkedin_profile_url": "https://www.linkedin.com/company/codesscafe",
                        "title": "Mentee",
                        "description": None,
                        "location": None,
                        "logo_url": "https://media.licdn.com/dms/image/C4D0BAQHSlNCmwwBsyw/company-logo_400_400/0/1662096135243/codesscafe_logo?e=1715817600&v=beta&t=9MB7z90_xHYVtzZtZ2XGf7OiD6P5D2IF04jlu9siQk4"
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 1,
                            "year": 2022
                        },
                        "ends_at": None,
                        "company": "CodXCrypt Community",
                        "company_linkedin_profile_url": "https://www.linkedin.com/company/codxcryptcommunity",
                        "title": "Mentee",
                        "description": "Skills: Leadership · Microsoft PowerPoint · Communication · Microsoft Word",
                        "location": None,
                        "logo_url": "https://media.licdn.com/dms/image/C4E0BAQEFgCdnfdJk2g/company-logo_400_400/0/1630617041087/codxcryptcommunity_logo?e=1715817600&v=beta&t=mbEwaA04Fjq8ol_Vxh_JafzVHlpAlBS0yLX45ztbbtY"
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 1,
                            "year": 2022
                        },
                        "ends_at": {
                            "day": 30,
                            "month": 4,
                            "year": 2023
                        },
                        "company": "CodXCrypt Community",
                        "company_linkedin_profile_url": "https://www.linkedin.com/company/codxcryptcommunity",
                        "title": "Web Designer",
                        "description": None,
                        "location": None,
                        "logo_url": "https://media.licdn.com/dms/image/C4E0BAQEFgCdnfdJk2g/company-logo_400_400/0/1630617041087/codxcryptcommunity_logo?e=1715817600&v=beta&t=mbEwaA04Fjq8ol_Vxh_JafzVHlpAlBS0yLX45ztbbtY"
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 11,
                            "year": 2022
                        },
                        "ends_at": None,
                        "company": "Hustlers Sunshine",
                        "company_linkedin_profile_url": "https://www.linkedin.com/company/87445126/",
                        "title": "Founder",
                        "description": "Helping students and working professionals to make their future bright .\nWe believe that every student, irrespective of their college or branch, can make it big. Hustlers Sunshine Community is an initiative built on this thought.\n\nWe provide hands-on training , guidance/mentorship, placement /job preparation resources , internship/ job opportunities and have an inclusive community.",
                        "location": "Jaipur, Rajasthan, India",
                        "logo_url": "https://media.licdn.com/dms/image/C4D0BAQH030N3jOnI3A/company-logo_400_400/0/1669523062101?e=1715817600&v=beta&t=FfMm-SIK94X9cmxNenaxRMlVwkrvRsjYy8WJkIdzWv4"
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 2,
                            "year": 2022
                        },
                        "ends_at": {
                            "day": 30,
                            "month": 4,
                            "year": 2023
                        },
                        "company": "Internshala",
                        "company_linkedin_profile_url": "https://www.linkedin.com/company/internshala",
                        "title": "Internshala Student Partner (ISP)",
                        "description": None,
                        "location": None,
                        "logo_url": "https://media.licdn.com/dms/image/C4D0BAQFi4GG2XwFHqQ/company-logo_400_400/0/1630487078763/internshala_logo?e=1715817600&v=beta&t=3-hzXoOg6HhuI3dWsOpPL6ds3oHhgYPkC4nB-6LYmr8"
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 3,
                            "year": 2022
                        },
                        "ends_at": {
                            "day": 30,
                            "month": 4,
                            "year": 2023
                        },
                        "company": "The Entrepreneurship Cell, VNIT Nagpur",
                        "company_linkedin_profile_url": "https://www.linkedin.com/company/theentrepreneurshipcellvnit",
                        "title": "Growth Hacker Intern",
                        "description": None,
                        "location": None,
                        "logo_url": "https://media.licdn.com/dms/image/D560BAQHVo1suVUSokg/company-logo_400_400/0/1692677853931?e=1715817600&v=beta&t=lo6qHimO1Ay5DkuP01nQcfWx1-BqFmD2oWlYg6Mj-s8"
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 2,
                            "year": 2022
                        },
                        "ends_at": {
                            "day": 30,
                            "month": 4,
                            "year": 2023
                        },
                        "company": "Codeflow",
                        "company_linkedin_profile_url": "https://www.linkedin.com/company/codefloworg",
                        "title": "Mentee",
                        "description": None,
                        "location": None,
                        "logo_url": "https://media.licdn.com/dms/image/C4D0BAQEPTtOHWVHqsA/company-logo_400_400/0/1630537247206/codefloworg_logo?e=1715817600&v=beta&t=ZAhk3VywrXci9cK8k2A2nTRiNGB_JbVEAMwBIp5D7-Q"
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 7,
                            "year": 2022
                        },
                        "ends_at": {
                            "day": 31,
                            "month": 8,
                            "year": 2022
                        },
                        "company": "Hacker Bro Technologies",
                        "company_linkedin_profile_url": "https://www.linkedin.com/company/hacker-bro-technologies",
                        "title": "Frontened developer ",
                        "description": None,
                        "location": None,
                        "logo_url": "https://media.licdn.com/dms/image/C4E0BAQG-u8Ffr7JXew/company-logo_400_400/0/1637322085024?e=1715817600&v=beta&t=ML_lg4sREv-jwTOmK18CKIZBfHdOaoGLX8fXEavVL6I"
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 7,
                            "year": 2022
                        },
                        "ends_at": {
                            "day": 31,
                            "month": 7,
                            "year": 2022
                        },
                        "company": "Goldman Sachs",
                        "company_linkedin_profile_url": "https://www.linkedin.com/company/goldman-sachs",
                        "title": "Software Engineer virtual internship ",
                        "description": None,
                        "location": None,
                        "logo_url": "https://media.licdn.com/dms/image/C4E0BAQHm5bYK6emQSg/company-logo_400_400/0/1630621204189/goldman_sachs_logo?e=1715817600&v=beta&t=KDCB8XT1F3w5t8I0SDivxP3g6tXALfso8ji9ZjW2q2w"
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 2,
                            "year": 2022
                        },
                        "ends_at": {
                            "day": 31,
                            "month": 7,
                            "year": 2022
                        },
                        "company": "Girl Code It - Pune",
                        "company_linkedin_profile_url": "https://www.linkedin.com/company/78991364/",
                        "title": "Mentee",
                        "description": None,
                        "location": None,
                        "logo_url": "https://media.licdn.com/dms/image/C4E0BAQHKIsjPFYFxmQ/company-logo_400_400/0/1643980906680/girl_code_it_pune_logo?e=1715817600&v=beta&t=tzvrYOjOV7lfoD7GQ5mYG5AqvrlVPUNrexkAh0kmNJs"
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 2,
                            "year": 2022
                        },
                        "ends_at": {
                            "day": 31,
                            "month": 3,
                            "year": 2022
                        },
                        "company": "JPMorgan Chase & Co.",
                        "company_linkedin_profile_url": "https://www.linkedin.com/company/jpmorganchase",
                        "title": "Software engineering Virtual internship",
                        "description": None,
                        "location": None,
                        "logo_url": "https://media.licdn.com/dms/image/C4E0BAQFN7ZGRjNcgeA/company-logo_400_400/0/1656681489601/jpmorganchase_logo?e=1715817600&v=beta&t=fDelMMQlMCkfZfAYBwr63Z50p0Gr_EHKjWDwH1Fef84"
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 3,
                            "year": 2022
                        },
                        "ends_at": {
                            "day": 31,
                            "month": 3,
                            "year": 2022
                        },
                        "company": "Walmart Global Tech India",
                        "company_linkedin_profile_url": "https://www.linkedin.com/company/walmartglobaltechindia",
                        "title": "Advanced software engineering virtual experience",
                        "description": None,
                        "location": None,
                        "logo_url": "https://media.licdn.com/dms/image/C4D0BAQEC3n4yU_w6bQ/company-logo_400_400/0/1630541053165/walmartglobaltechindia_logo?e=1715817600&v=beta&t=ZEt_ppmkbd7IMjnJxDTnZdm2oFVueO4M9boEvhaG9Jc"
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 7,
                            "year": 2021
                        },
                        "ends_at": {
                            "day": 31,
                            "month": 8,
                            "year": 2021
                        },
                        "company": "APPWARS  Technologies ",
                        "company_linkedin_profile_url": None,
                        "title": "Social Media Marketing Intern",
                        "description": None,
                        "location": None,
                        "logo_url": None
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 6,
                            "year": 2021
                        },
                        "ends_at": {
                            "day": 31,
                            "month": 8,
                            "year": 2021
                        },
                        "company": "Learnvern",
                        "company_linkedin_profile_url": "https://www.linkedin.com/company/learnvern",
                        "title": "Campus Ambassador",
                        "description": None,
                        "location": None,
                        "logo_url": "https://media.licdn.com/dms/image/C4E0BAQGnGu8LuPqxpA/company-logo_400_400/0/1630645172201/learnvern_logo?e=1715817600&v=beta&t=PCPDXbzZfd1mBjj_DC-lDpCmpvIjczpIIljYJ9iD1GY"
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 7,
                            "year": 2021
                        },
                        "ends_at": {
                            "day": 31,
                            "month": 8,
                            "year": 2021
                        },
                        "company": "CollegeTips.in",
                        "company_linkedin_profile_url": "https://www.linkedin.com/company/collegetips",
                        "title": "Intern",
                        "description": None,
                        "location": None,
                        "logo_url": "https://media.licdn.com/dms/image/C560BAQHLJ1NnqMO46A/company-logo_400_400/0/1630635238578?e=1715817600&v=beta&t=dLquzKzKBhmmycXiM5iI9Vnq9FA1uKNXPgnVLVpNU50"
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 5,
                            "year": 2021
                        },
                        "ends_at": {
                            "day": 31,
                            "month": 7,
                            "year": 2021
                        },
                        "company": "Great Learning",
                        "company_linkedin_profile_url": "https://www.linkedin.com/company/great-learning",
                        "title": "Campus Ambassador",
                        "description": None,
                        "location": "Mumbai, Maharashtra, India",
                        "logo_url": "https://media.licdn.com/dms/image/C560BAQF40lFj20_wxA/company-logo_400_400/0/1630649587188/great_learning_logo?e=1715817600&v=beta&t=VUOZ7T8j6oQTWkIyZe-qyGgDrFpYS2z6KH3lT-zCXaA"
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 6,
                            "year": 2021
                        },
                        "ends_at": {
                            "day": 30,
                            "month": 6,
                            "year": 2021
                        },
                        "company": "IFortis Corporate",
                        "company_linkedin_profile_url": "https://www.linkedin.com/company/ifortiscorp",
                        "title": "Intern",
                        "description": None,
                        "location": None,
                        "logo_url": "https://media.licdn.com/dms/image/C560BAQHzSFZwnf6ajg/company-logo_400_400/0/1630641473699?e=1715817600&v=beta&t=zUBlfoeIyJVyCAjOHyjeIcTAswjFjV4XXRTafLIAodg"
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 6,
                            "year": 2021
                        },
                        "ends_at": {
                            "day": 30,
                            "month": 6,
                            "year": 2021
                        },
                        "company": "SEEKHO",
                        "company_linkedin_profile_url": "https://www.linkedin.com/company/seekho-ai",
                        "title": "Engineer Intern",
                        "description": None,
                        "location": None,
                        "logo_url": "https://media.licdn.com/dms/image/C4D0BAQGpUYzB738STg/company-logo_400_400/0/1671940605578/seekho_ai_logo?e=1715817600&v=beta&t=9F-nsOWCa4J-PT18HZNUEF58fJu7wIO6EPaPluOGnwY"
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 8,
                            "year": 2018
                        },
                        "ends_at": {
                            "day": 29,
                            "month": 2,
                            "year": 2020
                        },
                        "company": "St. Joseph Convent School",
                        "company_linkedin_profile_url": "https://www.linkedin.com/company/st-joseph-s-convent-high-school",
                        "title": "Event Planner",
                        "description": None,
                        "location": "Jaipur, Rajasthan, India",
                        "logo_url": "https://media.licdn.com/dms/image/C510BAQEao6lsTI7hig/company-logo_400_400/0/1631414649174/st_joseph_s_convent_high_school_logo?e=1715817600&v=beta&t=Tx_gDLsiyOojwEf1BgqjVRP4oWTVjGvypgfLPQPF1M4"
                        }
                    ],
                    "education": [
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 1,
                            "year": 2020
                        },
                        "ends_at": {
                            "day": 31,
                            "month": 12,
                            "year": 2024
                        },
                        "field_of_study": "Engneering in CS",
                        "degree_name": "Bachelor of Technology - BTech",
                        "school": "Vivekanand Institute of Technology,Jaipur",
                        "school_linkedin_profile_url": "https://www.linkedin.com/company/15131041/",
                        "description": None,
                        "logo_url": None,
                        "grade": None,
                        "activities_and_societies": None
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 1,
                            "year": 2006
                        },
                        "ends_at": {
                            "day": 31,
                            "month": 12,
                            "year": 2020
                        },
                        "field_of_study": "P.C.M",
                        "degree_name": "Senior secondary",
                        "school": "ST. Joseph convent school ,jaipur",
                        "school_linkedin_profile_url": None,
                        "description": None,
                        "logo_url": None,
                        "grade": None,
                        "activities_and_societies": None
                        }
                    ],
                    "languages": [],
                    "accomplishment_organisations": [],
                    "accomplishment_publications": [],
                    "accomplishment_honors_awards": [],
                    "accomplishment_patents": [],
                    "accomplishment_courses": [
                        {
                        "name": "CSS",
                        "number": None
                        },
                        {
                        "name": "HTML5",
                        "number": None
                        }
                    ],
                    "accomplishment_projects": [],
                    "accomplishment_test_scores": [],
                    "volunteer_work": [
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 4,
                            "year": 2021
                        },
                        "ends_at": {
                            "day": 30,
                            "month": 6,
                            "year": 2021
                        },
                        "title": "Event Coordinator",
                        "cause": "Education",
                        "company": "Muskurahat Foundation",
                        "company_linkedin_profile_url": "https://www.linkedin.com/company/14390100/",
                        "description": None,
                        "logo_url": "https://media.licdn.com/dms/image/C560BAQEMoXp817ytrw/company-logo_400_400/0/1630650992477/muskurahat_foundation_logo?e=1715817600&v=beta&t=nvE_HojOWBI35KG1IS8zG2yrVjKO46bXR57XNvXRsiA"
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 5,
                            "year": 2021
                        },
                        "ends_at": {
                            "day": 31,
                            "month": 5,
                            "year": 2021
                        },
                        "title": "Event Planner",
                        "cause": "Education",
                        "company": "Aashman Foundation",
                        "company_linkedin_profile_url": None,
                        "description": None,
                        "logo_url": None
                        }
                    ],
                    "certifications": [
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 9,
                            "year": 2022
                        },
                        "ends_at": None,
                        "name": "DSA Course",
                        "license_number": "1aCxDu0VJB8",
                        "display_source": "devsnest.in",
                        "authority": "Devsnest",
                        "url": "https://devsnest.in/certificate/1aCxDu0VJB8"
                        },
                        {
                        "starts_at": {
                            "day": 1,
                            "month": 6,
                            "year": 2022
                        },
                        "ends_at": None,
                        "name": "100 Days of Code Winners",
                        "license_number": "bc73fef1-96d5-472f-b45f-8f7e0ac25c72",
                        "display_source": "devsnest.in",
                        "authority": "CodeIN Community ",
                        "url": "https://devsnest.in/certificate/1aCxDu0VJB8"
                        }
                    ],
                    "connections": 10012,
                    "people_also_viewed": [
                        {
                        "link": "https://www.linkedin.com/in/jyoti-bhasin-7840991ba",
                        "name": "Jyoti Bhasin",
                        "summary": "Microsoft Engage'22🔹Program Manager @GirlScript WOB🔹Managed 35+ Communities 🔹Co-Founder @CyberVerse🔹Partnerships @GDG Ludhiana🔹DevRel🔹Technical Writer🔹Data Science",
                        "location": None
                        },
                        {
                        "link": "https://www.linkedin.com/in/kashyapsrishti",
                        "name": "Srishti Kashyap",
                        "summary": "Software Engineer • 135k+ Followers • Open for Collaborations • Helping Brands to Grow • AI • Code & Content • Helping Jobseekers",
                        "location": None
                        },
                        {
                        "link": "https://www.linkedin.com/in/dev-raj-saini",
                        "name": "Dev Raj Saini",
                        "summary": "|| Founder || 190,000+ Follower || Helping Jobseekers || Entrepreneurship || Top Brand Development Voice || Top Personal Branding Voice || 250M+ Views ||",
                        "location": None
                        },
                        {
                        "link": "https://www.linkedin.com/in/atul3",
                        "name": "Atul Kumar",
                        "summary": "400K+ Brains | Building at Growth Eye | AI Enthusiast | Helping For Jobseekers | Building Personal Brands For Founders and  Start-ups | Social Media Growth, Planning & Management",
                        "location": None
                        },
                        {
                        "link": "https://www.linkedin.com/in/kiran-kanwar-r-b7129022a",
                        "name": "Kiran Kanwar R.",
                        "summary": "151K+ Followers🚀|| Software Developer || AI & Programming || DSA || Open for Collaborations || Helping Brands to Grow || 11K Telegram Community",
                        "location": None
                        }
                    ],
                    "recommendations": [
                        "Kamalesh Naran\n\n\n\nI have worked with Sandhya and was extremely satisfied with her level of service and turnaround time. I highly recommend her and will use her services in future too.",
                        "Sahir Maharaj\n\n\n\nIt is my pleasure to recommend Sandhya Mishra. I have had the opportunity to collaborate with Sandhya and have been impressed with her skills and dedication to her work. \n\nShe is a highly motivated individual who is always eager to take on new challenges and expand her skill set.\n\nHer expertise in programming, as well as her knowledge of subjects such as data structures and algorithms, make her a valuable asset to any team."
                    ],
                    "activities": [],
                    "similarly_named_profiles": [],
                    "articles": [],
                    "groups": [
                        {
                        "profile_pic_url": "https://media.licdn.com/dms/image/C4D07AQF4VBe3jyXA8A/group-logo_image-shrink_400x400/0/1630998390698?e=1708416000&v=beta&t=PKY88r4aBMw_gY_w9_jqghqMHSE3ihvzrSKnB1NHWIk",
                        "name": "IoT, Internet of Things, M2M, Smart Cities, Connected Home, Edge Computing, IIOT and Big Data",
                        "url": "https://www.linkedin.com/groups/8356116"
                        },
                        {
                        "profile_pic_url": "https://media.licdn.com/dms/image/C5607AQHTAaU6NT5IDA/group-logo_image-shrink_48x48/0/1631007936617?e=1708416000&v=beta&t=9E9VvEyKqrMLolwc_c9HOBYE8uC6mGenDEeC-vP0pbA",
                        "name": "Analytics and Artificial Intelligence (AI) in Marketing and Retail",
                        "url": "https://www.linkedin.com/groups/4371519"
                        }
                    ],
                    "skills": [
                        "Machine Learning",
                        "Market Segmentation",
                        "Go-to-Market Strategy",
                        "Competitive Analysis",
                        "Campaign Execution",
                        "Microsoft Word",
                        "Microsoft PowerPoint",
                        "Microsoft Excel",
                        "Leadership",
                        "Customer Service",
                        "Communication",
                        "Web Analytics",
                        "Proofreading",
                        "YouTube",
                        "Presentations",
                        "Instagram",
                        "Influencer Marketing",
                        "Creative Briefs",
                        "Campaign Strategies",
                        "Campaign Effectiveness",
                        "Brand Awareness",
                        "Consulting",
                        "HTML",
                        "Front-End Development",
                        "Engineering",
                        "Computer Science",
                        "Python (Programming Language)",
                        "Java",
                        "C (Programming Language)",
                        "C++",
                        "Linux",
                        "HTML5",
                        "English",
                        "Artificial Intelligence (AI)",
                        "CSS",
                        "JavaScript",
                        "WordPress",
                        "Adobe Photoshop",
                        "Dance",
                        "Web Development",
                        "Data structure and algorithm ",
                        "Guitar Playing",
                        "Node.js",
                        "React.js",
                        "GitHub",
                        "Git",
                        "Programming"
                    ],
                    "inferred_salary": None,
                    "gender": None,
                    "birth_date": None,
                    "industry": None,
                    "extra": None,
                    "interests": [],
                    "personal_emails": [],
                    "personal_numbers": []
                    }
                # if data.get('code') == 403:
                #     return Response({"message": "Rate limit exceeded. Please try again later."}, status=status.HTTP_403_FORBIDDEN)
                
                # if data.get('code') == 400:
                #     return Response({"message": "Rate limit exceeded. Please try again later."}, status=status.HTTP_400_BAD_REQUEST)
                
                # if data.get('code') == 401:
                #     return Response({"message": "Invalid API Key"}, status=status.HTTP_401_UNAUTHORIZED)
                
                # if data.get('code') == 429:
                #     return Response({"message": "Rate limited. Please retry"}, status=status.HTTP_429_TOO_MANY_REQUESTS)

                # print(data)
                # print(data.keys())


                city = data["city"]
                country = data["country_full_name"]
                # print(country)
                current_role = data["occupation"]
                education_levels = data["education"]
                education_levels = validate_education(education_levels)

                work_experience = data["experiences"]
                work_experience = validate_experience(work_experience)

                certifications = data["certifications"]
                certifications = validate_certifications(certifications)

                achievements = data["accomplishment_honors_awards"]
                achievements = validate_achievements(achievements)

                technical_skills = data["skills"]

                overall_experience = tech_skill_mapping(work_experience, technical_skills)

                restructured_data = {
                        "user_id": user_id,
                        "current_occupation":current_role,
                        "city" : city,
                        "country" : country,
                        "education":education_levels,
                        "experience":json.loads(overall_experience),
                        "certifications_and_courses":certifications,
                        "achievements_and_accolades":achievements,
                        "updated_at":datetime.datetime.now(),
                        "created_at":datetime.datetime.now()

                    }
                profile_id = resume_data.insert_one(restructured_data)
                restructured_data.pop('_id')
                # users_registration.update_one({'_id': ObjectId(user_id)}, {'$set': {"onboarding_process":{"step":5,"process":"Linkedin"}}})
                print(restructured_data)
                return restructured_data
            # except json.JSONDecodeError:
            #     return Response({"message":"Please upload the resume again"},status=status.HTTP_400_BAD_REQUEST)
            
            # except Exception as e:
            #         # Log the exception for debugging
            #     return Response({"message": "An error occurred", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)