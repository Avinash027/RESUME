
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
import os
from dotenv import load_dotenv

load_dotenv()

def load_document(file_path: str):
    if file_path.endswith(".pdf"):
        loader = PyPDFLoader(file_path)
    elif file_path.endswith(".docx"):
        loader = Docx2txtLoader(file_path)
    elif file_path.endswith(".txt"):
        loader = TextLoader(file_path)
    else:
        raise ValueError("Unsupported file type")
    return loader.load()

def extract_text_from_documents(documents) -> str:
    return "\n".join([doc.page_content for doc in documents])

def get_embeddings_model():
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    model_kwargs = {"device": "cpu"}
    encode_kwargs = {"normalize_embeddings": False}
    return HuggingFaceEmbeddings(model_name=model_name, model_kwargs=model_kwargs, encode_kwargs=encode_kwargs)

def get_rag_chain(resume_content: str, jd_content: str):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    resume_docs = text_splitter.create_documents([resume_content])
    jd_docs = text_splitter.create_documents([jd_content])

    embeddings = get_embeddings_model()

    vectorstore = FAISS.from_documents(resume_docs + jd_docs, embeddings)
    retriever = vectorstore.as_retriever()

    llm = ChatGroq(temperature=0, groq_api_key=os.getenv("GROQ_API_KEY"), model_name="llama3-8b-8192")

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True
    )
    return qa_chain

def get_matching_score_summary_and_edits(resume_text: str, jd_text: str):
    llm = ChatGroq(temperature=0, groq_api_key=os.getenv("GROQ_API_KEY"), model_name="llama3-8b-8192")
    
    prompt_template = """
    You are an AI assistant that specializes in matching resumes to job descriptions.
    Given a resume and a job description, perform the following tasks:
    1. Identify key skills from the resume that match the job description.
    2. Identify relevant project experience from the resume that aligns with the job requirements.
    3. Assess the overall compatibility between the resume and the job description.
    4. Generate a matching score out of 100, where 100 is a perfect match.
    5. Provide a concise summary explaining the matching score, highlighting strengths and weaknesses.
    6. Suggest specific edits to the resume to better match the job description. Provide these as a bulleted list.

    Resume: {resume}
    Job Description: {job_description}

    Please provide the output in the following format:

    Matching Score: [SCORE]/100
    Summary: [SUMMARY TEXT]
    Suggested Edits:
    - [EDIT 1]
    - [EDIT 2]
    - ...
    """

    formatted_prompt = prompt_template.format(resume=resume_text, job_description=jd_text)
    
    response = llm.invoke(formatted_prompt)
    
    response_text = response.content if hasattr(response, 'content') else str(response)
    
    score = None
    summary = ""
    suggested_edits = []
    
    lines = response_text.split('\n')
    
    current_section = None
    for line in lines:
        if 'Matching Score:' in line:
            current_section = 'score'
            try:
                score_part = line.split(':')[1].strip()
                score = int(score_part.split('/')[0])
            except (ValueError, IndexError):
                score = None
        elif 'Summary:' in line:
            current_section = 'summary'
            summary = line.split(':', 1)[1].strip()
        elif 'Suggested Edits:' in line:
            current_section = 'edits'
        elif current_section == 'edits' and line.strip().startswith('-'):
            suggested_edits.append(line.strip())
        elif current_section == 'summary':
            summary += "\n" + line.strip() # Append to summary if it's a multi-line summary
            
    return {"matching_score": score, "summary": summary, "suggested_edits": suggested_edits}


