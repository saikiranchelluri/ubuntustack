import os
import json
import uuid
from langchain.document_loaders import PyPDFLoader
from langchain.document_loaders import Docx2txtLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.chat_models import ChatOpenAI
from langchain.callbacks import get_openai_callback
from langchain.chains.question_answering import load_qa_chain
from youe_backend.settings import OPENAI_API_KEY


os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY


response_list = []

def resume_reader(uploaded_file, extension):
    unique_filename = str(uuid.uuid4())
    upload_directory = 'uploaded_files'
    os.makedirs(upload_directory, exist_ok=True)

    if extension.endswith('pdf'):
        temp_file_path = os.path.join(upload_directory, f'{unique_filename}.pdf')
        with open(temp_file_path, 'wb') as f:
            f.write(uploaded_file.read())
        file_size = os.path.getsize(temp_file_path)
        max_size_bytes = 2000000 
        if file_size > max_size_bytes:
            return 1
        pdf_loader = PyPDFLoader(temp_file_path)
        documents = pdf_loader.load()
        page_content = documents[0].page_content
        if page_content == "":
            return False
    elif extension.endswith('docx'):
        temp_file_path = os.path.join(upload_directory, f'{unique_filename}.docx')
        with open(temp_file_path, 'wb') as f:
            f.write(uploaded_file.read())
        file_size = os.path.getsize(temp_file_path)
        max_size_bytes = 2000000 
        if file_size > max_size_bytes:
            return 1
        doc_loader = Docx2txtLoader(temp_file_path)
        documents = doc_loader.load()
        page_content = documents[0].page_content
        # print(page_content)
        if page_content == "":
            return False
   
    os.remove(temp_file_path)  

    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    documents = text_splitter.split_documents(documents)   

    query = 'your task is to retrieve the Information:name,city,country,education_levels(university,degree,specialisation,start_date,end_date),current_role and company,list work_experience(role,company,industry,function,start_date,end_date,tech_skills(#list max 5 skills gained through the role)),soft_skills(max 6 items),hobbies(max 6 items),certifications_held(#null if no related data found else return :title,from_organization,exhibited_on(return only end_date),description(limit to 30 words)),professional_associations(#null if no related data found else return :association_name,start_date,end_date,description(limit to 30 words)),achievements_and_accolades(#null if no related data found else return :title,from_organization,exhibited_on(return only end_date),description(limit to 30 words)) from the given resume.Please return the response in JSON format without any explanations and replace null if relevant data not found for any key.Also maintain this date format(Date format :%B %Y) wherever you find the date value.'    
    chain = load_qa_chain(llm=ChatOpenAI(temperature=0.2, model="gpt-3.5-turbo-16k"))
    with get_openai_callback() as cb:
        response = chain.run(input_documents=[doc for doc in documents], question=query)

        tokens = {
            "Total Tokens": cb.total_tokens,
            "Prompt Tokens": cb.prompt_tokens,
            "Completion Tokens": cb.completion_tokens,
            "Total Cost (USD)": f"${cb.total_cost}"
        }
        # print(tokens)
    total_cost=tokens["Total Cost (USD)"]
    # print(response)
    return json.loads(response),total_cost


    
   
