"""
MongoDB document helpers for Doubt Solver collections.
Replaces SQLAlchemy ORM models with direct PyMongo CRUD operations.
"""

import bcrypt
from datetime import datetime, timedelta
from bson import ObjectId
from .database import get_db, to_str_id

CHAT_EXPIRY_DAYS = 7


# ═══════════════════════════════════════════════════════════
#  StudentProfile helpers
# ═══════════════════════════════════════════════════════════

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_password(password, password_hash):
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def create_student_profile(name, roll_no, password):
    db = get_db()
    doc = {
        "name": name,
        "roll_no": roll_no,
        "password_hash": hash_password(password),
        "created_at": datetime.utcnow(),
    }
    result = db.student_profiles.insert_one(doc)
    doc["_id"] = result.inserted_id
    return to_str_id(doc)


def get_profile_by_roll_no(roll_no):
    db = get_db()
    doc = db.student_profiles.find_one({"roll_no": roll_no})
    return to_str_id(doc) if doc else None


def get_profile_by_id(profile_id):
    db = get_db()
    doc = db.student_profiles.find_one({"_id": ObjectId(profile_id)})
    return to_str_id(doc) if doc else None


# ═══════════════════════════════════════════════════════════
#  StudentDocument helpers
# ═══════════════════════════════════════════════════════════

def create_student_document(student_id, original_filename, stored_filename, vectorstore_path):
    db = get_db()
    doc = {
        "student_id": student_id,
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "vectorstore_path": vectorstore_path,
        "uploaded_at": datetime.utcnow(),
    }
    result = db.student_documents.insert_one(doc)
    doc["_id"] = result.inserted_id
    return to_str_id(doc)


def get_document_by_id(document_id):
    db = get_db()
    doc = db.student_documents.find_one({"_id": ObjectId(document_id)})
    return to_str_id(doc) if doc else None


def get_documents_by_student(student_id):
    db = get_db()
    return [to_str_id(d) for d in db.student_documents.find({"student_id": student_id}).sort("uploaded_at", -1)]


# ═══════════════════════════════════════════════════════════
#  DoubtChatSession helpers
# ═══════════════════════════════════════════════════════════

def create_doubt_session(student_id, document_id, title="New Chat"):
    db = get_db()
    now = datetime.utcnow()
    doc = {
        "student_id": student_id,
        "document_id": document_id,
        "title": title,
        "created_at": now,
        "last_active_at": now,
        "expires_at": now + timedelta(days=CHAT_EXPIRY_DAYS),
        "is_active": True,
    }
    result = db.doubt_chat_sessions.insert_one(doc)
    doc["_id"] = result.inserted_id
    return to_str_id(doc)


def get_doubt_session_by_id(session_id):
    db = get_db()
    doc = db.doubt_chat_sessions.find_one({"_id": ObjectId(session_id)})
    return to_str_id(doc) if doc else None


def update_doubt_session(session_id, updates):
    db = get_db()
    db.doubt_chat_sessions.update_one({"_id": ObjectId(session_id)}, {"$set": updates})


def get_active_sessions_by_student(student_id):
    db = get_db()
    return [to_str_id(s) for s in db.doubt_chat_sessions.find(
        {"student_id": student_id, "is_active": True}
    ).sort("last_active_at", -1)]


def is_session_expired(session_doc):
    return datetime.utcnow() > session_doc.get("expires_at", datetime.utcnow())


# ═══════════════════════════════════════════════════════════
#  ChatMessage helpers
# ═══════════════════════════════════════════════════════════

def create_chat_message(session_id, role, content, sources=None):
    db = get_db()
    doc = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "sources": sources,
        "created_at": datetime.utcnow(),
    }
    result = db.chat_messages.insert_one(doc)
    doc["_id"] = result.inserted_id
    return to_str_id(doc)


def get_messages_by_session(session_id):
    db = get_db()
    return [to_str_id(m) for m in db.chat_messages.find({"session_id": session_id}).sort("created_at", 1)]


def count_messages_by_session(session_id):
    db = get_db()
    return db.chat_messages.count_documents({"session_id": session_id})


def cleanup_expired_doubt_sessions():
    """Deactivate all expired doubt chat sessions."""
    db = get_db()
    cutoff = datetime.utcnow()
    result = db.doubt_chat_sessions.update_many(
        {"expires_at": {"$lt": cutoff}, "is_active": True},
        {"$set": {"is_active": False}},
    )
    count = result.modified_count
    print(f"[DoubtSolver] Cleaned up {count} expired sessions")
    return count
