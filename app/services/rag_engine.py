"""
RAG Engine — Public API for quiz question generation.
Now delegates to LangGraph Agent A internally.
"""

import os
import random
from flask import current_app
from .langgraph_agents import run_quiz_agent


def process_pdf_and_generate_pool(pdf_path, session_code):
    """
    Complete pipeline called at PDF upload time.
    Delegates to LangGraph Agent A (Quiz Question Generator).
    Returns a list of question dicts.
    """
    vectorstore_dir = os.path.join(current_app.root_path, 'static', 'vectorstores')
    os.makedirs(vectorstore_dir, exist_ok=True)

    print(f"[RAG Engine] Delegating to LangGraph Agent A for session {session_code}...")
    questions = run_quiz_agent(pdf_path, session_code, vectorstore_dir)
    print(f"[RAG Engine] Agent A returned {len(questions)} questions")
    return questions


def pick_random_questions_for_student(session_questions, count=20):
    """Picks `count` random questions from the session pool."""
    if len(session_questions) <= count:
        return list(session_questions)
    return random.sample(list(session_questions), count)