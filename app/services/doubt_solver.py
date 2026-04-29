"""
Doubt Solver Service — orchestrates PDF uploads, chat sessions, and Agent B.
Uses IST timezone for all display timestamps.
"""

import os
import json
from datetime import datetime, timedelta
from flask import current_app
from ..models.database import db
from ..models.chat import (
    StudentProfile, StudentDocument, DoubtChatSession, ChatMessage, CHAT_EXPIRY_DAYS
)
from .langgraph_agents import run_doubt_agent, get_embeddings
from .timezone import to_local, to_local_short
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS


def register_profile(name: str, roll_no: str, password: str) -> StudentProfile:
    """Register a new student profile with hashed password."""
    existing = StudentProfile.query.filter_by(roll_no=roll_no).first()
    if existing:
        raise ValueError("Roll number already registered. Please login instead.")

    profile = StudentProfile(name=name, roll_no=roll_no)
    profile.set_password(password)
    db.session.add(profile)
    db.session.commit()
    print(f"[DoubtSolver] New profile registered: {name} ({roll_no})")
    return profile


def authenticate_profile(roll_no: str, password: str) -> StudentProfile:
    """Authenticate a student with roll_no + password."""
    profile = StudentProfile.query.filter_by(roll_no=roll_no).first()
    if not profile:
        return None
    if not profile.check_password(password):
        return None
    return profile


def process_student_pdf(student_id: int, file_obj, original_filename: str) -> StudentDocument:
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
    doc = StudentDocument(
        student_id=student_id,
        original_filename=original_filename,
        stored_filename=stored_name,
        vectorstore_path=vs_dir,
    )
    db.session.add(doc)
    db.session.commit()

    print(f"[DoubtSolver] PDF processed: {original_filename} → {len(chunks)} chunks")
    return doc


def create_chat_session(student_id: int, document_id: int, title: str = "New Chat") -> DoubtChatSession:
    """Create a new doubt chat session linked to a document."""
    session = DoubtChatSession(
        student_id=student_id,
        document_id=document_id,
        title=title,
    )
    db.session.add(session)
    db.session.commit()
    return session


def send_message(session_id: int, query: str, requesting_student_id: int) -> dict:
    """
    Process a student message:
    1. Verify ownership
    2. Save the user message
    3. Load chat history
    4. Run Agent B
    5. Save and return the AI response
    """
    chat_session = DoubtChatSession.query.get(session_id)
    if not chat_session:
        return {"error": "Chat session not found"}

    # Security: verify the requesting student owns this chat
    if chat_session.student_id != requesting_student_id:
        return {"error": "Access denied. This chat belongs to another student."}

    if chat_session.is_expired:
        chat_session.is_active = False
        db.session.commit()
        return {"error": "This chat session has expired (7-day limit reached)."}

    doc = chat_session.document
    if not doc or not doc.vectorstore_path:
        return {"error": "No PDF linked to this chat. Please upload a PDF first."}

    # 1. Save user message
    user_msg = ChatMessage(session_id=session_id, role="user", content=query)
    db.session.add(user_msg)

    # 2. Build chat history for context
    history = [
        {"role": m.role, "content": m.content}
        for m in chat_session.messages
    ]

    # 3. Run Agent B
    result = run_doubt_agent(
        query=query,
        vectorstore_path=doc.vectorstore_path,
        chat_history=history,
    )

    # 4. Save AI response
    sources_json = json.dumps(result.get("sources", []))
    ai_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=result["answer"],
        sources=sources_json,
    )
    db.session.add(ai_msg)

    # Update session title from first question
    if len(history) == 0:
        chat_session.title = query[:80] + ("..." if len(query) > 80 else "")

    chat_session.last_active_at = datetime.utcnow()
    db.session.commit()

    return {
        "answer": result["answer"],
        "sources": result.get("sources", []),
        "message_id": ai_msg.id,
    }


def get_chat_history(student_id: int) -> list:
    """Get all active (non-expired) chat sessions for a student."""
    sessions = DoubtChatSession.query.filter_by(
        student_id=student_id, is_active=True
    ).order_by(DoubtChatSession.last_active_at.desc()).all()

    result = []
    for s in sessions:
        if s.is_expired:
            s.is_active = False
            continue
        result.append({
            "id": s.id,
            "title": s.title,
            "document": s.document.original_filename if s.document else None,
            "created_at": to_local(s.created_at),
            "last_active": to_local(s.last_active_at),
            "expires_at": to_local(s.expires_at),
            "message_count": len(s.messages),
        })

    db.session.commit()  # persist any expiry changes
    return result


def get_session_messages(session_id: int, requesting_student_id: int) -> dict:
    """Get all messages in a chat session (with ownership check)."""
    session = DoubtChatSession.query.get(session_id)
    if not session:
        return {"error": "Session not found"}

    if session.student_id != requesting_student_id:
        return {"error": "Access denied"}

    messages = ChatMessage.query.filter_by(session_id=session_id)\
        .order_by(ChatMessage.created_at).all()

    return {
        "messages": [{
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "sources": json.loads(m.sources) if m.sources else [],
            "created_at": to_local(m.created_at),
        } for m in messages],
        "title": session.title,
        "document": session.document.original_filename if session.document else None,
    }


def cleanup_expired_sessions():
    """Deactivate expired chat sessions (lazy cleanup)."""
    cutoff = datetime.utcnow()
    expired = DoubtChatSession.query.filter(
        DoubtChatSession.expires_at < cutoff,
        DoubtChatSession.is_active == True
    ).all()

    count = 0
    for session in expired:
        session.is_active = False
        count += 1

    db.session.commit()
    print(f"[DoubtSolver] Cleaned up {count} expired sessions")
    return count
