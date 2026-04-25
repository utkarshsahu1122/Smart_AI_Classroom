import os
import json
import random
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from flask import current_app

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# LLM Configuration — single model, no fallback
LLM_MODEL = "gemini-2.5-flash"


def get_embeddings():
    """Returns a local embedding model (free, fast, no API dependency)."""
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def _estimate_question_count(num_pages):
    """Estimate a good question pool size based on the PDF length."""
    if num_pages <= 3:
        return 30
    elif num_pages <= 10:
        return 50
    elif num_pages <= 25:
        return 70
    else:
        return 100


def process_pdf_and_generate_pool(pdf_path, session_code):
    """
    Complete pipeline called at PDF upload time:
    1. Extract and chunk PDF text
    2. Build FAISS vectorstore
    3. Use RAG to generate a large pool of high-quality questions
    Returns a list of question dicts.
    """
    # --- Step 1: Load and chunk ---
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    num_pages = len(docs)
    full_text = "\n\n".join([doc.page_content for doc in docs])

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)

    # --- Step 2: Build vectorstore ---
    embeddings = get_embeddings()
    vectorstore = FAISS.from_documents(splits, embeddings)

    vs_path = os.path.join(current_app.root_path, 'static', 'vectorstores', session_code)
    os.makedirs(vs_path, exist_ok=True)
    vectorstore.save_local(vs_path)

    # --- Step 3: Generate question pool ---
    target_count = _estimate_question_count(num_pages)
    print(f"[RAG Engine] PDF has {num_pages} pages. Generating pool of ~{target_count} questions...")

    # Retrieve diverse chunks using multiple semantic queries
    query_topics = [
        "key concepts and definitions",
        "important principles and theories",
        "examples and applications",
        "comparisons and differences",
        "processes and procedures",
        "advantages and limitations",
        "summary and conclusions",
    ]

    all_context_chunks = []
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    for topic in query_topics:
        retrieved = retriever.invoke(topic)
        for doc in retrieved:
            if doc.page_content not in all_context_chunks:
                all_context_chunks.append(doc.page_content)

    combined_context = "\n\n---\n\n".join(all_context_chunks)

    # --- Step 4: Call LLM with improved prompt ---
    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        temperature=0.8,
        google_api_key=GOOGLE_API_KEY
    )

    prompt = PromptTemplate.from_template(
        """You are a highly experienced university professor designing a comprehensive assessment.

TASK: Generate exactly {num_questions} high-quality quiz questions from the provided course material.

CRITICAL RULES:
1. DO NOT copy-paste sentences from the material as questions. Every question must be REPHRASED in your own words.
2. Questions must TEST UNDERSTANDING — ask about concepts, relationships, applications, and reasoning. Not rote memorisation.
3. For MCQs: all 4 options must be plausible. The wrong options should be realistic distractors, not obviously silly.
4. For Fill-in-the-blanks: use a meaningful sentence that tests a KEY TERM or CONCEPT. The blank should be a single important word or short phrase.
5. Cover DIFFERENT topics and sections from the material. Spread questions evenly across the content.
6. Mix difficulty: include some easy recall questions, some moderate application questions, and some challenging analytical questions.
7. Produce roughly 70% MCQs and 30% Fill-in-the-blanks.

OUTPUT FORMAT: Return ONLY a valid JSON array. Each object must have:
- "question_text": The question (for fill_blank, use ______ to mark the blank)
- "question_type": "mcq" or "fill_blank"
- "options": A list of exactly 4 option strings (for mcq). Empty list [] for fill_blank.
- "correct_answer": The exact correct answer string

COURSE MATERIAL:
{context}

Generate {num_questions} questions now. JSON array only, no extra text:"""
    )

    chain = prompt | llm

    try:
        print(f"[RAG Engine] Calling {LLM_MODEL} to generate {target_count} questions...")
        response = chain.invoke({"num_questions": target_count, "context": combined_context})

        raw_json = response.content.replace("```json", "").replace("```", "").strip()
        quiz_data = json.loads(raw_json)
        print(f"[RAG Engine] SUCCESS! Generated {len(quiz_data)} questions for session {session_code}")
        return quiz_data

    except Exception as e:
        print(f"[RAG Engine] ERROR generating questions: {e}")
        return []


def pick_random_questions_for_student(session_questions, count=10):
    """
    Picks `count` random questions from the session pool.
    Returns a list of QuizQuestion model instances.
    """
    if len(session_questions) <= count:
        return list(session_questions)
    return random.sample(list(session_questions), count)