from django.shortcuts import render

# Create your views here.
import pymongo
from bson import ObjectId
from langchain.prompts import StringPromptTemplate
from typing import Any, Dict, List, Optional
from langchain.llms import OpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts.prompt import PromptTemplate
import os
from rest_framework import status
from rest_framework.response import Response
from users.mongoDb_connection import dashboard_data,users_registration,youechatbot_collection,resume_data
from rest_framework.views import APIView
import uuid
from youe_backend.settings import OPENAI_API_KEY
from datetime import datetime

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

class ExtendedConversationBufferMemory(ConversationBufferMemory):
    extra_variables:List[str] = []

    @property
    def memory_variables(self) -> List[str]:
        """Will always return list of memory variables."""
        return [self.memory_key] + self.extra_variables

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Return buffer with history and extra variables"""
        d = super().load_memory_variables(inputs)
        d.update({k:inputs.get(k) for k in self.extra_variables})        
        return d
    
class GenerateChatIdView(APIView):
    def get(self, request, user_id):
        #try:
            if not user_id:
                    return Response({'message': 'Please provide a User Id'}, status=status.HTTP_400_BAD_REQUEST)

            user = users_registration.find_one({"_id": ObjectId(user_id)})
            if not user:
                    return Response({'message': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
            else:             
                chat_id= str(uuid.uuid4())
                insert_data=youechatbot_collection.insert_one({"user_id":user_id,"chat_id": chat_id,"created_at":datetime.now()})
                return Response({"chat_id": chat_id},status=status.HTTP_200_OK)
       # except Exception as e:
           # return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class YoueAiChatbotView(APIView):
    def post(self, request):
        try:
            user_id = request.data.get('user_id')
            chat_id = request.data.get('chat_id')
            user_prompt= request.data.get('prompt')
            if not user_id:
                        return Response({'message': 'Please provide a User Id'}, status=status.HTTP_400_BAD_REQUEST)
            if not chat_id:
                        return Response({'message': 'Please provide a Chat Id'}, status=status.HTTP_400_BAD_REQUEST)
            if not user_prompt:
                        return Response({'message': 'Please give a prompt'}, status=status.HTTP_400_BAD_REQUEST)
            user = users_registration.find_one({"_id": ObjectId(user_id)})
            if not user:
                return Response({'message': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
            chat_conversation = youechatbot_collection.find_one({"chat_id": chat_id})
            if not chat_conversation:
                return Response({"message": "Chat Id doesn't exist"}, status=status.HTTP_400_BAD_REQUEST)

            nodemap = dashboard_data.find_one({'user_id':user_id})
            milestones=nodemap.get('milestones')
            profile=resume_data.find_one({'user_id':user_id})
            chat = chat_conversation.get("chat")

            llm = OpenAI(model_name='gpt-3.5-turbo-16k',temperature=0)
            #memory=ConversationBufferMemory(ai_prefix="AI Assistant")
            memory=ExtendedConversationBufferMemory(extra_variables=["profile","milestones"])
            # Iterate over the conversation history and add each prompt and answer to the ConversationBufferMemory instance
            if chat:
                for user_conversation in chat:
                    print(user_conversation)
                    memory.save_context({"input":user_conversation['prompt']},{"output":user_conversation['response']})
        
            template = """The following is a conversation between a human and an AI.Answer the human's question in a way 
            that is relevant to the profile(which has education, work experience, skills,courses etc). 
            The profile data is {profile}.The human is currently following a road map which is {milestones} .The AI is a career
            guidance expert and provides lots of specific details from its context.

            If the human's input is related to their profile and road map:
            Generate a response using the conversation history and the human's profile and road map as input.
            
            If the human's input is not related to their profile,road map and career:
            Say "Please ask something related to your skills,road map or career."

            Current conversation:
            {history}
            Human: {input}
            AI Assistant:"""
            # PROMPT = CustomPromptTemplate(
            #     input_variables=["history", "input"], template=template,user_name=username,skills=skills,experience=experience
            # )
            PROMPT = PromptTemplate(input_variables=["history", "input","profile","milestones"], template=template)
            #PROMPT = PromptTemplate(input_variables=["history", "input"],template=template)
            conversation_chain = ConversationChain(
                prompt=PROMPT,
                llm=llm,
                verbose=True,
                memory=memory,
            )
            #output=conversation_chain.predict(input=prompt)
            #output=conversation_chain({"input": prompt, "user_name":username,"skills":skills,"experience":experience})
            output=conversation_chain.predict(input=user_prompt,profile=profile,milestones=milestones)

            print("memory:",memory.buffer)
            print("output:",output)
            if chat: #if a chat already exists
                update = {"$push": {"chat": {"prompt": user_prompt,"response": output}},
                           "$set": {"last_interacted": datetime.now()}}
                youechatbot_collection.update_one({
                     'chat_id': chat_id}, update
                     )
            else:
                chat_data={
                     "chat": [{
                                        "prompt": user_prompt,
                                        "response": output
                }],
                "last_interacted":datetime.now()
                }
                youechatbot_collection.update_one({'chat_id': chat_id}, {'$set':chat_data})
                
            return Response({"response": output},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
     

class ConversationHistoryView(APIView):
    def get(self, request,user_id):
        try:
            if not id:
                return Response({'message': 'Please provide a User Id'}, status=status.HTTP_400_BAD_REQUEST)
                  
            user = users_registration.find_one({"_id": ObjectId(user_id)})
            if not user:
                    return Response({'message': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
            pipeline = [
    {
        "$match": {
            "user_id": user_id,
            "chat": {
                "$exists": True
            },
            "last_interacted": {"$lt": datetime.now()}
        }
    },
    {
        "$sort": {
            "last_interacted": -1
        }
    },
    {
        "$limit": 5
    },
    {
        "$group": {
            "_id": "$user_id",
            "conversation_history": {
                "$push": {
                    "chat_id": "$chat_id",
                    "chat": "$chat"
                }
            }
        }
    }
]
            # Execute the aggregation pipeline
            results = youechatbot_collection.aggregate(pipeline)
            # final_response=list(results)
            # final_response["response"][0]["user_id"] = final_response["response"][0].pop("_id")
            print(results)
            return Response({"response": results},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


