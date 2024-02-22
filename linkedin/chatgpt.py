import os
import json
import uuid
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.callbacks import get_openai_callback
from langchain.document_loaders import PyPDFLoader
from langchain.document_loaders import Docx2txtLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains.question_answering import load_qa_chain
from youe_backend.settings import OPENAI_API_KEY


os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY


response_list = []

def tech_skill_mapping(work_experience, technical_skills):
    

    # query = 'your task is to retrieve the Information:name,city,country,education_levels(university,degree,specialisation,start_date,end_date),current_role and company,list work_experience(role,company,industry,function,start_date,end_date,tech_skills(#list max 5 skills gained through the role)),soft_skills(max 6 items),hobbies(max 6 items),certifications_held(#null if no related data found else return :title,from_organization,exhibited_on(return only end_date),description(limit to 30 words)),professional_associations(#null if no related data found else return :association_name,start_date,end_date,description(limit to 30 words)),achievements_and_accolades(#null if no related data found else return :title,from_organization,exhibited_on(return only end_date),description(limit to 30 words)) from the given resume.Please return the response in JSON format without any explanations and replace null if relevant data not found for any key.Also maintain this date format(Date format :%B %Y) wherever you find the date value.'    
    query = f'{work_experience} . This is my experience. Help me map my experience with the skills given below in the skills key {technical_skills}. Return the response in the same format with the key tech_skills (max 5 skills)inside each experience object. Please return the response in proper Json format without any explanation and without creating a separate array in {work_experience}.'
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
    print("respnse" ,response)
    # print(response)
    total_cost = tokens.get('Total Cost (USD)')
    return response


    
   
