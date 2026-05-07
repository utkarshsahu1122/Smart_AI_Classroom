"""
MongoDB document helpers for Quiz system collections.
Replaces SQLAlchemy ORM models with direct PyMongo CRUD operations.
"""

from datetime import datetime
from bson import ObjectId
from .database import get_db, to_str_id


# ═══════════════════════════════════════════════════════════
#  QuizSession helpers
# ═══════════════════════════════════════════════════════════

def create_quiz_session(session_code, pdf_filename, qr_code_path, timer_minutes=10, mcq_weight=70, fill_weight=30):
    db = get_db()
    doc = {
        "session_code": session_code,
        "pdf_filename": pdf_filename,
        "qr_code_path": qr_code_path,
        "created_at": datetime.utcnow(),
        "timer_minutes": timer_minutes,
        "mcq_weight": mcq_weight,
        "fill_weight": fill_weight,
        "questions_generated": True,
        "is_active": True,
        "ended_at": None,
    }
    result = db.quiz_sessions.insert_one(doc)
    doc["_id"] = result.inserted_id
    return to_str_id(doc)


def get_quiz_session_by_code(session_code):
    db = get_db()
    doc = db.quiz_sessions.find_one({"session_code": session_code})
    return to_str_id(doc) if doc else None


def get_quiz_session_by_id(session_id):
    db = get_db()
    doc = db.quiz_sessions.find_one({"_id": ObjectId(session_id)})
    return to_str_id(doc) if doc else None


def update_quiz_session(session_id, updates):
    db = get_db()
    db.quiz_sessions.update_one({"_id": ObjectId(session_id)}, {"$set": updates})


# ═══════════════════════════════════════════════════════════
#  QuizQuestion helpers
# ═══════════════════════════════════════════════════════════

def insert_quiz_questions(session_id, questions_data):
    """Insert a batch of questions for a session. Returns inserted count."""
    db = get_db()
    docs = []
    for q in questions_data:
        opts = "|".join(q.get("options", [])) if q.get("options") else ""
        docs.append({
            "session_id": session_id,
            "question_text": q["question_text"],
            "question_type": q["question_type"],
            "options": opts,
            "correct_answer": q["correct_answer"],
        })
    if docs:
        db.quiz_questions.insert_many(docs)
    return len(docs)


def get_questions_by_session(session_id):
    db = get_db()
    return [to_str_id(q) for q in db.quiz_questions.find({"session_id": session_id})]


def get_question_by_id(question_id):
    db = get_db()
    doc = db.quiz_questions.find_one({"_id": ObjectId(question_id)})
    return to_str_id(doc) if doc else None


# ═══════════════════════════════════════════════════════════
#  Student helpers
# ═══════════════════════════════════════════════════════════

def create_student(session_id, name, roll_no):
    db = get_db()
    doc = {
        "session_id": session_id,
        "name": name,
        "roll_no": roll_no,
        "score": 0,
        "submitted_at": None,
        "is_logged_in": True,
        "warning_count": 0,
        "unfair_means": False,
        "submission_reason": "manual",
    }
    result = db.students.insert_one(doc)
    doc["_id"] = result.inserted_id
    return to_str_id(doc)


def get_student_by_id(student_id):
    db = get_db()
    doc = db.students.find_one({"_id": ObjectId(student_id)})
    return to_str_id(doc) if doc else None


def get_student_by_session_and_roll(session_id, roll_no):
    db = get_db()
    doc = db.students.find_one({"session_id": session_id, "roll_no": roll_no})
    return to_str_id(doc) if doc else None


def get_students_by_session(session_id):
    db = get_db()
    return [to_str_id(s) for s in db.students.find({"session_id": session_id}).sort("roll_no", 1)]


def update_student(student_id, updates):
    db = get_db()
    db.students.update_one({"_id": ObjectId(student_id)}, {"$set": updates})


# ═══════════════════════════════════════════════════════════
#  StudentQuestion helpers (links student → assigned questions)
# ═══════════════════════════════════════════════════════════

def assign_questions_to_student(student_id, question_ids):
    """Assign a list of question IDs to a student."""
    db = get_db()
    docs = [{"student_id": student_id, "question_id": qid, "student_answer": None} for qid in question_ids]
    if docs:
        db.student_questions.insert_many(docs)
    return len(docs)


def get_assigned_questions(student_id):
    """Get all assigned question links for a student, with full question data."""
    db = get_db()
    assignments = list(db.student_questions.find({"student_id": student_id}))
    result = []
    for sq in assignments:
        q = db.quiz_questions.find_one({"_id": ObjectId(sq["question_id"])})
        if q:
            result.append({
                "sq_id": str(sq["_id"]),
                "student_id": sq["student_id"],
                "question_id": sq["question_id"],
                "student_answer": sq.get("student_answer"),
                "question": to_str_id(q),
            })
    return result


def update_student_answer(student_id, question_id, answer):
    db = get_db()
    db.student_questions.update_one(
        {"student_id": student_id, "question_id": question_id},
        {"$set": {"student_answer": answer}},
    )


def count_assigned_questions(student_id):
    db = get_db()
    return db.student_questions.count_documents({"student_id": student_id})
