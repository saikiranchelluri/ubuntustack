import os
import json
import openai
import pandas as pd
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.callbacks import get_openai_callback
from youe_backend.settings import OPENAI_API_KEY

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
def edit_milestones_gpt(journey_list,new_title,milestone_data):
   
   query = f"I have a chosen career path referred to as '{journey_list}' and have established a set of milestones and related actions within a nodemap for this career path. Please take a look at the milestone details: {milestone_data}. now i want  to update the milestone's title by replacing milestone_data['title'] with  a new title called '{new_title}'. Could you please evaluate if this new title is aligned with the career path I've previously established? Simply respond with 'yes' if the new title is suitable, or 'no' if it's not, without providing any explanation."
   model="gpt-4"
   temp=0.7

   llm = ChatOpenAI(model=model,temperature=temp)
   prompt = PromptTemplate(
   input_variables=["edit_milestone"],
   template = "{edit_milestone}"
        )
   chain = LLMChain(llm=llm, prompt=prompt)
   with get_openai_callback() as cb:
            response_data = chain.run({
                                "edit_milestone":query
                                })
   tokens = {
                "Total Tokens": cb.total_tokens,
                "Prompt Tokens": cb.prompt_tokens,
                "Completion Tokens": cb.completion_tokens,
                "Total Cost (USD)": f"${cb.total_cost}"
            }
   print(tokens)
   cost_data = tokens["Total Cost (USD)"]
#    response = json.loads(response)
   response=response_data.lower()
   print(response)
   return response,cost_data





def Add_Actions_For_milestones_gpt(journey_list,new_title,milestone_data,timeline,path_1,path_2):
   
   response_1 = pd.read_excel(path_1).to_json(orient="records")
   milestone_1 = json.loads(response_1)
   response_2 = pd.read_excel(path_2).to_json(orient="records")
   milestone_2 = json.loads(response_2)
   query = f"""I'm following a specific career path, which I refer to as {journey_list}.and have established a set of milestones and related actions within a nodemap for this career path. Please take a look at the milestone details: {milestone_data}.now i want  to update the milestone's title by replacing milestone_data['title'] with  a new title called '{new_title}'. 
                for this {new_title},Analyse the milestone_data["category"] category and From {milestone_1}or{milestone_2} and analyse milestone['actions_to_track_and_complete'] details into consideration while  generating particular actions  for that milestone(Please do not return these  milestone['milestone_category'] and milestone['actions_to_track_and_complete'] value in milestone 'title' and action 'title' response). please  provide only this two details don't give any other details:
                    1. Milestone Description (key: 'milestone_description'): Describe the milestone.
                    2. Actions (key: 'actions'): Suggest up to maximum 5 actions to achieve the milestone.
                    3.Allocate a duration for each action from the provided timeline {timeline}  (key: 'duration' - format:  X days(s) ). Also,provide the ’title’ (# specifying any online courses, platforms, projects, or institutes along with the title  that can help achieve the action)and ‘description’ for each action.
                    4. Provide up to three critical enablers (key: 'enablers') chosen from the list: [Growth mindset, Self-discipline, Optimism, Proactivity, Reflective thinking, Self-awareness, Attitude, Strategic thinking, Goal-setting, Creativity, Analytical thinking, Financial literacy, Learning agility, Leadership, Adaptability, Flexibility, Cultural competence, Conflict resolution, Active listening, Decision-making, Relationship building, Feedback-seeking]. For each enabler value, use the key "title".
                    Please format the response in JSON and ensure that it contains only these two specified details without any explanation.
"""
   model="gpt-4"
   temp=0.7
   llm = ChatOpenAI(model=model,temperature=temp)
   prompt = PromptTemplate(
   input_variables=["edit_milestone"],
   template = "{edit_milestone}"
        )
   chain = LLMChain(llm=llm, prompt=prompt)
   with get_openai_callback() as cb:
            response = chain.run({
                                "edit_milestone":query
                                })
   tokens = {
                "Total Tokens": cb.total_tokens,
                "Prompt Tokens": cb.prompt_tokens,
                "Completion Tokens": cb.completion_tokens,
                "Total Cost (USD)": f"${cb.total_cost}"
            }
   print(tokens)
   cost_data = tokens["Total Cost (USD)"]
        
   response = json.loads(response)
#    print(response)
 
   return response,cost_data


def Add_Actions_For_milestones_gpt1(journey_list,new_title,milestone_data_with_timeline,path_1,path_2):
   
   response_1 = pd.read_excel(path_1).to_json(orient="records")
   milestone_1 = json.loads(response_1)
   response_2 = pd.read_excel(path_2).to_json(orient="records")
   milestone_2 = json.loads(response_2)
   query = f"""
I'm following a specific career path, which I refer to as {journey_list}.and have established a set of milestones and related actions within a nodemap for this career path. Please take a look at the milestone details: {milestone_data_with_timeline}.now i want  to update the milestone's title by replacing milestone_data_with_timeline['title'] with  a new title called '{new_title}with  a new title called '{new_title}'. for this {new_title},Analyse the milestone_data_with_timeline["category"]  category and From {milestone_1} or {milestone_2}  and analyse milestone['actions_to_track_and_complete'] details into consideration while  generating particular actions  for that milestone(Please do not return these  milestone['milestone_category'] and milestone['actions_to_track_and_complete'] value in milestone 'title' and action 'title' response).  provide only this two details don't give any other details:
                    1. Milestone Description (key: 'milestone_description'): Describe the milestone.
                  
                    
                    2. Actions (key: 'actions'): Suggest up to maximum 5 actions to achieve the milestone.
                     
                    3.please check this milestone_data_with_timeline["timeline"] timeline  and  Allocate a duration for each actions by deviding this milestone_data_with_timeline["timeline"] timeline (key: 'duration' - format:  X days(s) )). Also,provide the ’title’ (# specifying any online courses, platforms, projects, or institutes along with the title  that can help achieve the action)and ‘description’ for each action.
                    4. Provide up to three critical enablers (key: 'enablers') chosen from the list: [Growth mindset, Self-discipline, Optimism, Proactivity, Reflective thinking, Self-awareness, Attitude, Strategic thinking, Goal-setting, Creativity, Analytical thinking, Financial literacy, Learning agility, Leadership, Adaptability, Flexibility, Cultural competence, Conflict resolution, Active listening, Decision-making, Relationship building, Feedback-seeking]. For each enabler value, use the key "title".
                    don't give any other details what i mention in this prompt only give this details.Please return the response in JSON format with out any explanation.
"""
   model="gpt-4"
   temp=0.7
   llm = ChatOpenAI(model=model,temperature=temp)
   prompt = PromptTemplate(
   input_variables=["edit_milestone"],
   template = "{edit_milestone}"
        )
   chain = LLMChain(llm=llm, prompt=prompt)
   with get_openai_callback() as cb:
            response = chain.run({
                                "edit_milestone":query
                                })
   tokens = {
                "Total Tokens": cb.total_tokens,
                "Prompt Tokens": cb.prompt_tokens,
                "Completion Tokens": cb.completion_tokens,
                "Total Cost (USD)": f"${cb.total_cost}"
            }
   print(tokens)
   cost_data = tokens["Total Cost (USD)"]
   response = json.loads(response)
#    print(response)
 
   return response,cost_data


#validate milestone title for add milestone
def Add_milestones_validate_title_gpt(journey_list,new_title):
   

   query = f"I have chosen a specific career path referred to as '{journey_list}' and have established a series of milestones and corresponding actions in a nodemap for this career path. Now, I wish to introduce a new milestone with the title '{new_title}' within this nodemap. Please evaluate whether this new title is in alignment with the career path I have previously defined. Kindly respond with 'yes' if the new title is pertinent, or 'no' if it is not, without the need for an explanation."   
   model="gpt-4"
   temp=0.7
   llm = ChatOpenAI(model=model,temperature=temp)
   prompt = PromptTemplate(
   input_variables=["add_milestone_validate_title"],
   template = "{add_milestone_validate_title}"
        )
   chain = LLMChain(llm=llm, prompt=prompt)
   with get_openai_callback() as cb:
            response_data = chain.run({
                                "add_milestone_validate_title":query
                                })
   tokens = {
                "Total Tokens": cb.total_tokens,
                "Prompt Tokens": cb.prompt_tokens,
                "Completion Tokens": cb.completion_tokens,
                "Total Cost (USD)": f"${cb.total_cost}"
            }
   print(tokens)
   cost_data = tokens["Total Cost (USD)"]
        
   response=response_data.lower()
   print(response)
 
   return response,cost_data




#Add only milestone
#completed
def Add_milestones_gpt(new_title,path_1,path_2):
   
   response_1 = pd.read_excel(path_1).to_json(orient="records")
   milestone_1 = json.loads(response_1)
   response_2 = pd.read_excel(path_2).to_json(orient="records")
   milestone_2 = json.loads(response_2)
   query = f"""I'm following a specific career path and have established a set of milestones and related actions within a nodemap for that career path.

Now, I'd like to add a new milestone with the title {new_title}. In JSON format, please provide the following details for this new milestone, without including any additional information:

1. Milestone Description (key: 'milestone_description'):  Provide a brief description of the milestone.
2. Milestone Type (key: 'type'): Specify that it's a milestone.
3. Consider the {milestone_1} or {milestone_2}  and analysis milestone['milestone_category']  when generating this milestone. However,(please do not include the milestone['milestone_category']  value in the milestone 'title.' Instead, provide the milestone category using the (key :category)

Please format the response in JSON without  any explanation.
."""
   model="gpt-4"
   temp=0.7
   llm = ChatOpenAI(model=model,temperature=temp)
   prompt = PromptTemplate(
   input_variables=["add_milestone"],
   template = "{add_milestone}"
        )
   chain = LLMChain(llm=llm, prompt=prompt)
   with get_openai_callback() as cb:
            response_data = chain.run({
                                "add_milestone":query
                                })
   tokens = {
                "Total Tokens": cb.total_tokens,
                "Prompt Tokens": cb.prompt_tokens,
                "Completion Tokens": cb.completion_tokens,
                "Total Cost (USD)": f"${cb.total_cost}"
            }
   print(tokens)
   cost_data = tokens["Total Cost (USD)"]
        
   response = json.loads(response_data)
   print(response)
 
   return response,cost_data

#completed
#add action and ce
def Add_actions_ce_for_milestone_gpt(new_title,timeline,path_1,path_2):
   
   response_1 = pd.read_excel(path_1).to_json(orient="records")
   milestone_1 = json.loads(response_1)
   response_2 = pd.read_excel(path_2).to_json(orient="records")
   milestone_2 = json.loads(response_2)
   query = f""" 
 
 
I'm following a specific career path  and i have established a set of milestones and related actions within a nodemap for this career path. Now, I'd like to create a new milestone with the title {new_title} and specify actions and enablers for its achievement.

For the new milestone, please provide the following details in JSON format do not give any other details:

1. Title (key: 'title'): The title will be {new_title}.
2. Milestone Description (key: 'milestone_description'): Offer a concise description of the milestone.
3. Milestone Type (key: 'type'): Specify whether it's a milestone.
4. Actions (key: 'actions'): Suggest up to maximum 5 actions to achieve the milestone.
5. When generating the milestone and individual actions, consider the  milestone['milestone_category'] and milestone['actions_to_track_and_complete'] details from {milestone_1} or {milestone_2}.  while generating the milestones and  while generating particular actions  for that milestone(Please do not return these  milestone['milestone_category'] and milestone['actions_to_track_and_complete'] value in milestone 'title' and action 'title' response). specify the milestone category (key: 'category').
6. Allocate a duration for each actions  (key: 'duration' - format:  X days(s) by dividing the ‘duration’ within this new milestone {timeline} timeline ). Include a 'title' (# specify any online courses, platforms, projects, or institutes) and 'description' for each action.
7. Provide up to three critical enablers (key: 'enablers') chosen from the list: [Growth mindset, Self-discipline, Optimism, Proactivity, Reflective thinking, Self-awareness, Attitude, Strategic thinking, Goal-setting, Creativity, Analytical thinking, Financial literacy, Learning agility, Leadership, Adaptability, Flexibility, Cultural competence, Conflict resolution, Active listening, Decision-making, Relationship building, Feedback-seeking]. For each enabler value, use the key "title".

Please ensure that the response is formatted in JSON without  any explanation.


"""
   model="gpt-4"
   temp=0.7
   llm = ChatOpenAI(model=model,temperature=temp)
   prompt = PromptTemplate(
   input_variables=["add_milestone"],
   template = "{add_milestone}"
        )
   chain = LLMChain(llm=llm, prompt=prompt)
   with get_openai_callback() as cb:
            response_data = chain.run({
                                "add_milestone":query
                                })
   tokens = {
                "Total Tokens": cb.total_tokens,
                "Prompt Tokens": cb.prompt_tokens,
                "Completion Tokens": cb.completion_tokens,
                "Total Cost (USD)": f"${cb.total_cost}"
            }
   print(tokens)
   cost_data = tokens["Total Cost (USD)"]
        
   response = json.loads(response_data)
   # print(response)
 
   return response,cost_data

