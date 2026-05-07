"""
Doubt Solver Service — orchestrates PDF uploads, chat sessions, and Agent B.
Uses IST timezone for all display timestamps.
Now uses MongoDB for all persistence.
"""

import os
import json
from datetime import datetime, timedelta
from flask import current_app
from ..models.chat import (
    create_student_profile, get_profile_by_roll_no, check_password,
    create_student_document, get_document_by_id,
    create_doubt_session, get_doubt_session_by_id, update_doubt_session,
    get_active_sessions_by_student, is_session_expired,
    create_chat_message, get_messages_by_session, count_messages_by_session,
    cleanup_expired_doubt_sessions,
)
from .langgraph_agents import run_doubt_agent, get_embeddings
from .timezone import to_local, to_local_short
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS


def register_profile(name: str, roll_no: str, password: str) -> dict:
    """Register a new student profile with hashed password."""
    existing = get_profile_by_roll_no(roll_no)
    if existing:
        raise ValueError("Roll number already registered. Please login instead.")

    profile = create_student_profile(name, roll_no, password)
    print(f"[DoubtSolver] New profile registered: {name} ({roll_no})")
    return profile


def authenticate_profile(roll_no: str, password: str):
    """Authenticate a student with roll_no + password."""
    profile = get_profile_by_roll_no(roll_no)
    if not profile:
        return None
    if not check_password(password, profile['password_hash']):
        return None
    return profile


def process_student_pdf(student_id: str, file_obj, original_filename: str) -> dict:
    """Save and vectorize a student-uploaded PDF."""
    from werkzeug.utils import secure_filename

    # Save PDF
    uploads_dir = os.path.join(current_app.root_path, 'static', 'doubt_uploads')
    os.makedirs(uploads_dir, exist_ok=True)

    safe_name = secure_filename(original_filename)
    stored_name = f"{student_id}_{int(datetime.utcnow().timestamp())}_{safe_name}"
    file_path = os.path.join(uploads_dir, stored_name)
    file_obj.save(file_path)

    # Build vectorstore
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)

    embeddings = get_embeddings()
    vectorstore = FAISS.from_documents(chunks, embeddings)

    vs_dir = os.path.join(
        current_app.root_path, 'static', 'doubt_vectorstores',
        str(student_id), stored_name.rsplit('.', 1)[0]
    )
    os.makedirs(vs_dir, exist_ok=True)
    vectorstore.save_local(vs_dir)

    # Save record
    doc = create_student_document(
        student_id=student_id,
        original_filename=original_filename,
        stored_filename=stored_name,
        vectorstore_path=vs_dir,
    )

    print(f"[DoubtSolver] PDF processed: {original_filename} → {len(chunks)} chunks")
    return doc


def create_chat_session(student_id: str, document_id: str, title: str = "New Chat") -> dict:
    """Create a new doubt chat session linked to a document."""
    session = create_doubt_session(
        student_id=student_id,
        document_id=document_id,
        title=title,
    )
    return session


def send_message(session_id: str, query: str, requesting_student_id: str) -> dict:
    """
    Process a student message:
    1. Verify ownership
    2. Save the user message
    3. Load chat history
    4. Run Agent B
    5. Save and return the AI response
    """
    chat_session = get_doubt_session_by_id(session_id)
    if not chat_session:
        return {"error": "Chat session not found"}

    # Security: verify the requesting student owns this chat
    if chat_session['student_id'] != requesting_student_id:
        return {"error": "Access denied. This chat belongs to another student."}

    if is_session_expired(chat_session):
        update_doubt_session(session_id, {"is_active": False})
        return {"error": "This chat session has expired (7-day limit reached)."}

    doc = get_document_by_id(chat_session['document_id'])
    if not doc or not doc.get('vectorstore_path'):
        return {"error": "No PDF linked to this chat. Please upload a PDF first."}

    # 1. Save user message
    create_chat_message(session_id=session_id, role="user", content=query)

    # 2. Build chat history for context
    messages = get_messages_by_session(session_id)
    history = [
        {"role": m['role'], "content": m['content']}
        for m in messages
    ]

    # 3. Run Agent B
    result = run_doubt_agent(
        query=query,
        vectorstore_path=doc['vectorstore_path'],
        chat_history=history,
    )

    # 4. Save AI response
    sources_json = json.dumps(result.get("sources", []))
    ai_msg = create_chat_message(
        session_id=session_id,
        role="assistant",
        content=result["answer"],
        sources=sources_json,
    )

    # Update session title from first question
    updates = {"last_active_at": datetime.utcnow()}
    if len(history) <= 1:  # First exchange (just the user message we added)
        updates["title"] = query[:80] + ("..." if len(query) > 80 else "")

    update_doubt_session(session_id, updates)

    return {
        "answer": result["answer"],
        "sources": result.get("sources", []),
        "message_id": ai_msg['id'],
    }


def get_chat_history(student_id: str) -> list:
    """Get all active (non-expired) chat sessions for a student."""
    sessions = get_active_sessions_by_student(student_id)

    result = []
    for s in sessions:
        if is_session_expired(s):
            update_doubt_session(s['id'], {"is_active": False})
            continue

        doc = get_document_by_id(s.get('document_id'))
        msg_count = count_messages_by_session(s['id'])

        result.append({
            "id": s['id'],
            "title": s.get('title', 'New Chat'),
            "document": doc['original_filename'] if doc else None,
            "created_at": to_local(s['created_at']),
            "last_active": to_local(s.get('last_active_at')),
            "expires_at": to_local(s.get('expires_at')),
            "message_count": msg_count,
        })

    return result


def get_session_messages(session_id: str, requesting_student_id: str) -> dict:
    """Get all messages in a chat session (with ownership check)."""
    session = get_doubt_session_by_id(session_id)
    if not session:
        return {"error": "Session not found"}

    if session['student_id'] != requesting_student_id:
        return {"error": "Access denied"}

    messages = get_messages_by_session(session_id)
    doc = get_document_by_id(session.get('document_id'))

    return {
        "messages": [{
            "id": m['id'],
            "role": m['role'],
            "content": m['content'],
            "sources": json.loads(m['sources']) if m.get('sources') else [],
            "created_at": to_local(m['created_at']),
        } for m in messages],
        "title": session.get('title', 'New Chat'),
        "document": doc['original_filename'] if doc else None,
    }


def cleanup_expired_sessions():
    """Deactivate expired chat sessions (lazy cleanup)."""
    return cleanup_expired_doubt_sessions()
