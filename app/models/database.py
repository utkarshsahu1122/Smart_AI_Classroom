"""
MongoDB connection module — connects to MongoDB Atlas or local MongoDB.
Uses PyMongo for direct, production-ready document operations.
"""

import os
import sys
from pymongo import MongoClient
from bson import ObjectId

# Module-level references (initialized in init_db)
_client = None
_db = None


def init_db(app):
    """Initialize the MongoDB connection using MONGO_URI from environment."""
    global _client, _db

    mongo_uri = os.environ.get('MONGO_URI')
    if not mongo_uri:
        raise Exception("MONGO_URI environment variable is not set")

    db_name = os.environ.get('MONGO_DB_NAME', 'smart_classroom')

    print("Loaded Mongo URI")

    try:
        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        # Force a connection test
        _client.admin.command('ping')
        _db = _client[db_name]
        print("Connected to MongoDB Atlas")
        _create_indexes()
    except Exception as e:
        print("MongoDB connection failed")
        sys.exit(1)


def get_db():
    """Return the active MongoDB database instance."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db


def _create_indexes():
    """Create indexes on frequently queried fields for performance."""
    db = get_db()

    # Quiz collections
    db.quiz_sessions.create_index("session_code", unique=True)
    db.quiz_questions.create_index("session_id")
    db.students.create_index([("session_id", 1), ("roll_no", 1)], unique=True)
    db.student_questions.create_index("student_id")
    db.student_questions.create_index("question_id")

    # Doubt solver collections
    db.student_profiles.create_index("roll_no", unique=True)
    db.student_documents.create_index("student_id")
    db.doubt_chat_sessions.create_index("student_id")
    db.doubt_chat_sessions.create_index("document_id")
    db.chat_messages.create_index("session_id")

    print("[MongoDB] Indexes created/verified.")


def to_str_id(doc):
    """Convert a MongoDB document's _id (ObjectId) to a string 'id' field."""
    if doc and '_id' in doc:
        doc['id'] = str(doc['_id'])
    return doc
