import os
import json
import openai
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.callbacks import get_openai_callback
from youe_backend.settings import OPENAI_API_KEY

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
#Edit action validate title
def edit_actions_gpt_update(journey_list,new_title,mile_data,action_id):
   query = f"I'm following a specific career path, as outlined in '{journey_list},' and I'v developed a roadmap with milestones and their associated actions.Please take a look at the milestone details: {mile_data}. My current task is to update the title of a specific action, identified by the action ID miledata['actions']['action_id'] with a new title '{new_title}'.  This action is associated with an action ID {action_id}. and this action id associated with this milestone ID mile_data['milestones']['milestone_id'] .Please evaluate whether the new action title  aligns with the chosen career path and the specific action identified by '{action_id}' that I've previously defined. Respond with 'yes' if the new title is relevant, and 'no' if it's not, without providing any explanation."
   model="gpt-4"
   temp=0.7
   llm = ChatOpenAI(model=model,temperature=temp)
   prompt = PromptTemplate(
   input_variables=["edit_action"],
   template = "{edit_action}"
        )
   chain = LLMChain(llm=llm, prompt=prompt)
   with get_openai_callback() as cb:
            response_data = chain.run({
                                "edit_action":query
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
   
 
   return response,cost_data


def add_actions_gpt(journey_list,new_title,milestone_data,milestone_id):

   
   # query = f"I have chosen a specific career path known as {selected_runway}. As a result, I've generated a set of milestones and related actions represented in a nodemap {nodemap} for this {selected_runway}. My current task is to update the action title of a particular action with a new title called {new_title}. This  new action  title i will update under the actions of this milestone ID {milestone_id}. Please evaluate the details and advise whether the new title is associate with actions list that comes under this {milestone_id},career path, nodemap, and the specific milestone {milestone_id} that I've previously generated. Respond with 'yes' if the new title is relevant, and 'no' if it's not with out any explanation."
   query = f"I'm following a specific career path, as outlined in '{journey_list},' and I've developed a roadmap with milestones and their associated actions. I'm currently considering adding a new action with the title '{new_title}' to the milestone ID {milestone_id}, which is aligned with the details in {milestone_data}. I'm seeking your opinion on whether this new action title '{new_title}' is suitable for the milestone details {milestone_data} and the career path I've previously established. Please respond with a simple 'yes' if the new title is fitting, and 'no' if it isn't, without any explanation."
   model="gpt-4"
   temp=0.7
   llm = ChatOpenAI(model=model,temperature=temp)
   prompt = PromptTemplate(
   input_variables=["add_action"],
   template = "{add_action}"
        )
   chain = LLMChain(llm=llm, prompt=prompt)
   with get_openai_callback() as cb:
            response_data = chain.run({
                                "add_action":query
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

 
   return response,cost_data



     
def generate_description_actions_gpt(journey_list,new_title,milestone_data):
   
   query = f"I have a chosen career path referred to as '{journey_list}' and have established a set of milestones and related actions within a nodemap for this career path.My current task is to add a new action with new title{new_title} .This  new action  title i will add under  this this {milestone_data}. your  task is for this {new_title} please generate a short description ( specifying any online courses, platforms, projects, or institutes along with the title  that can help achieve the action) (key:description) don't give any other details .please return resoponse in json without any explanation."
   model="gpt-4"
   temp=0.7
   llm = ChatOpenAI(model=model,temperature=temp)
   prompt = PromptTemplate(
   input_variables=["add_action"],
   template = "{add_action}"
        )
   chain = LLMChain(llm=llm, prompt=prompt)
   with get_openai_callback() as cb:
            response_data = chain.run({
                                "add_action":query
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

 
   return response,cost_data