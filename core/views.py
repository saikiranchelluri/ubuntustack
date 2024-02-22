from bson import ObjectId
import datetime 
from django.http import request
from rest_framework.response import Response
from django.http import JsonResponse
from django.core.paginator import Paginator
from bson import json_util
from rest_framework.views import APIView
import json
import os
from rest_framework import status,generics
from users.mongoDb_connection import users_registration,nudges, nudge_preference,resources,resume_data
from django.core.files.storage import default_storage
from urllib.parse import urljoin
from core.mixins import nudge_preference as np_post

# Create your views here.

nudge_type_mapping = {
    1: 'milestones',
    2: 'actions',
    3: 'critical_enablers',
    4: 'recommendations',
    # Add more mappings as needed
}

class NudgePreferenceView(APIView):

    def post(self, request, user_id):
        np_post(user_id=user_id)
        return Response ('success')
    
    def get(self, request, user_id):
        data = nudge_preference.find_one({'user_id': str(user_id)})
        if data:
            return Response(data['nudge_preference'])
        else:
            return Response({'message': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, user_id):
        try:
            user_data = request.data

            existing_user = nudge_preference.find_one({'user_id': str(user_id)})

            if existing_user:
                current_datetime = datetime.datetime.now()
                updated_preferences = {
                    'updated_on': current_datetime,
                }

                for nudge_type, preferences in user_data.items():
                    nudge_type = int(nudge_type)  # Convert the nudge_type to an integer
                    email_notification = preferences.get('email_notification')
                    web_notification = preferences.get('web_notification')

                    # Check if the provided nudge type is a valid number
                    if nudge_type > 0:
                        nudge_type_str = nudge_type_mapping.get(nudge_type)  # Get the nudge type string
                        if nudge_type_str:
                            nudge_type_key = f'{nudge_type_str}.nudge_type'
                            updated_preferences[f'nudge_preference.{nudge_type_str}'] = {
                                nudge_type_key: nudge_type,
                                'email_notification': email_notification,
                                'in_app_notification': web_notification,
                                'updated_on': current_datetime
                            }

                # Update the preferences for multiple nudge types
                nudge_preference.update_one(
                    {'user_id': str(user_id)},
                    {'$set': updated_preferences}
                )

                return Response({
                    "message": "Nudge Preferences have been updated",
                    "user_id": user_id
                }, status=status.HTTP_200_OK)

            else:
                return Response({'message': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class Search_Filter(APIView):
    def get(self, request):
        query = request.GET.get('q', '')
        tags = request.GET.getlist('tag')
        content_type=request.GET.get('content_type')

        pipeline = []
 
        match_criteria = {
            '$or': [
                {'title': {'$regex': query, '$options': 'i'}},
                {'category': {'$regex': query, '$options': 'i'}},
                {'description': {'$regex': query, '$options': 'i'}}
            ]
        }

        pipeline.append({
            '$match': match_criteria
        })

        
        if tags:
            tag_criteria = []

            for tag in tags:
                tag_criteria.append({'tag': {'$regex': tag, '$options': 'i'}})

            pipeline.append({
                '$match': {
                    '$or': tag_criteria
                }
            })


        if content_type:
            pipeline.append({
                '$match': {
                    'content_type': {'$regex': content_type, '$options': 'i'},
                }
            })

        results = list(resources.aggregate(pipeline))

        
        total_results = len(results)

        for result in results:
            result['_id'] = str(result['_id'])

      
        per_page = int(request.GET.get('per_page', 10)) 

       
        paginator = Paginator(results, per_page)

       
        page_number = request.GET.get('page',1)

       
        page = paginator.get_page(page_number)

        paginated_results = list(page)
    
        pagination_info = {
            'total_results': total_results,
            'current_page': page.number,
            'total_pages': paginator.num_pages,
        }

        response_data = {
            'results': paginated_results,
            'pagination_info': pagination_info,
        }
        return Response(response_data)

	
class Resources(APIView):
    

    def get(self, request):
        try:
           
            resources_cursor = resources.find({})  
            total_results = resources.count_documents({})
            resources_list = [resource for resource in resources_cursor]
            for resource in resources_list:
                resource['_id'] = str(resource['_id'])

            per_page = int(request.GET.get('per_page', 10))

            paginator = Paginator(resources_list, per_page)

            # Get the current page number from the request's GET parameters
            page_number = request.GET.get('page',1)

            # Get the Page object for the current page
            page = paginator.get_page(page_number)

            paginated_results = list(page)
        
            pagination_info = {
                'total_results': total_results,
                'current_page': page.number,
                'total_pages': paginator.num_pages,
            }

            # Include pagination information in the response data
            response_data = {
                'results': paginated_results,
                'pagination_info': pagination_info,
            }
            return Response(response_data)
        except Exception as e:
            
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        request_data = request.body
        data = json.loads(request_data)
        Category=data.get("category")
        Content_Type=data.get("content_type")
        Title=data.get("title")
        Description=data.get("description")
        Author=data.get("author")
        Link=data.get("resource_link")
        Tag=data.get("tag")
        published_on=data.get("published_on")
        


        if data:
            existing_resource = resources.find_one({"title": data.get("title")})

            if existing_resource:
                return Response({"message": "Resource with this title already exists"}, status=status.HTTP_409_CONFLICT)
            restructured_data = {
                "category": Category,
                "content_type":Content_Type,
                "title":Title,
                "description":Description,
                "author":Author,
                "resource_link":Link,
                "tag":Tag,
                "published_on":published_on,
                "updated_at":datetime.datetime.now(),
                "created_at":datetime.datetime.now()
        }
            
            resource_id = resources.insert_one(restructured_data).inserted_id
            return Response({"message": "Resource added successfully", "id": str(resource_id)}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "No data given"}, status=status.HTTP_400_BAD_REQUEST)
   
    def patch(self, request, id):
        # Retrieve data from the request
        request_data = request.body
        data = json.loads(request_data)
        Category=data.get("category")
        Content_Type=data.get("content_type")
        Title=data.get("title")
        Description=data.get("description")
        Author=data.get("author")
        Link=data.get("resource_link")
        Tag=data.get("tag")
        published_on=data.get("published_on")


        if data:
            existing_resource = resources.find_one({"title": data.get("title")})

        if existing_resource:
            # Check the file extension for the thumbnail
            restructured_data = {
                "category": Category,
                "content_type":Content_Type,
                "title":Title,
                "description":Description,
                "author":Author,
                "resource_link":Link,
                "tag":Tag,
                "published_on":published_on,
                "updated_at":datetime.datetime.now()
        }

                # Update the resource
            resources.update_one({'_id': ObjectId(id)}, {"$set": restructured_data})

            return Response({"message": "Resource updated successfully", "id": id}, status=status.HTTP_200_OK)

        else:
            return Response({"message": "Resource not found"}, status=status.HTTP_400_BAD_REQUEST)



    def delete(self, request, id): 
        try:
            obj = resources.find_one({"_id": ObjectId(id)})
            print("Object:", obj)
            if obj:
                resources.delete_one({"_id": ObjectId(id)})
                return Response({"message": "Resource deleted successfully."}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "No result found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "An error occurred: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)

class SearchByKeywords(APIView):
    def get(self, request, pk):
        # Initialize a set to store unique keywords
        unique_keywords = set()
        resources.create_index([("title", "text"), ("category", "text"), ("description", "text")])

        # Search in the profile collection
        profile = resume_data.find_one({'user_id': str(pk)})
        if profile:
            experiences = profile.get('experience', [])
            if experiences :  
                for exp in experiences:
                    tech_skills = exp.get('tech_skills', [])
                    for skill in tech_skills:
                        unique_keywords.add(skill.lower())

        # Search in the user collection (similar to the profile search)
        user = users_registration.find_one({'_id': ObjectId(pk)})
        if user:
            # Modify this part to retrieve keywords from the user collection
            user_journey = user.get('questionnaire', {}).get('selected_user_journey', {})

            if user_journey:

            # Extract the roles (targeted, intermediate, and current roles) from the user journey
                targeted_role = user_journey.get('targeted_role', {})
                intermediate_roles = user_journey.get('intermediate_roles', [])
                current_role = user_journey.get('current_role', {})

                # Combine the fields of all roles for searching
                all_roles = [targeted_role] + intermediate_roles + [current_role]

                for role in all_roles:
                    for skill in role.values():
                        unique_keywords.add(skill.lower())

        # Initialize a list to store results from the user collection
        user_results = []
        print("unique: ",unique_keywords )
        # Process the unique keywords
        for key in unique_keywords:
            query = {
                "$text": {"$search": key}
            }
            user_results += list(resources.find(query))


        combined_results = user_results  
   
        unique_resources = {} 

        for result in combined_results:
            unique_id = result.get('_id') 
            if unique_id not in unique_resources:
                unique_resources[unique_id] = result
                print("unique_id",unique_id)
                print("result",result)

        unique_results = list(unique_resources.values())

        if not unique_results:
            return Response({"message": "No recommendations found"}, status=status.HTTP_400_BAD_REQUEST)

        for result in unique_results:
            result['_id'] = str(result['_id'])

        return Response(unique_results)

class Tags(APIView):
    def get(self, request):
        pipeline = [
        {"$unwind": "$tag"},
        {"$group": {"_id": "$tag", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]

        top_tags = list(resources.aggregate(pipeline))

        top_tags = [tag["_id"] for tag in top_tags]
        return Response({"tags": top_tags}, status=status.HTTP_200_OK)
