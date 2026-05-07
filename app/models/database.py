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
        print("[Warning] MONGO_URI environment variable is not set. Starting without database.")
        return

    db_name = os.environ.get('MONGO_DB_NAME', 'smart_classroom')

    print("Loaded Mongo URI")

    try:
        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        # CosmosDB compatibility: wrap ping
        try:
            _client.admin.command('ping')
        except Exception as e:
            print(f"[Warning] CosmosDB ping failed or unsupported: {e}")
            
        _db = _client[db_name]
        print("Connected to MongoDB Atlas / CosmosDB")
        
        # CosmosDB compatibility: wrap overall index creation
        try:
            _create_indexes()
        except Exception as e:
            print(f"[Warning] Failed to initialize indexes: {e}")
            
    except Exception as e:
        print(f"[Warning] MongoDB connection failed: {e}. Starting without database connection.")


def get_db():
    """Return the active MongoDB database instance."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db


def _create_indexes():
    """Create indexes on frequently queried fields for performance."""
    db = get_db()

    def safe_create_index(collection, *args, **kwargs):
        try:
            collection.create_index(*args, **kwargs)
        except Exception as e:
            print(f"[Warning] Index creation failed on {collection.name} (CosmosDB compatibility): {e}")

    # Quiz collections
    safe_create_index(db.quiz_sessions, "session_code", unique=True)
    safe_create_index(db.quiz_questions, "session_id")
    safe_create_index(db.students, [("session_id", 1), ("roll_no", 1)], unique=True)
    safe_create_index(db.student_questions, "student_id")
    safe_create_index(db.student_questions, "question_id")

    # Doubt solver collections
    safe_create_index(db.student_profiles, "roll_no", unique=True)
    safe_create_index(db.student_documents, "student_id")
    safe_create_index(db.doubt_chat_sessions, "student_id")
    safe_create_index(db.doubt_chat_sessions, "document_id")
    safe_create_index(db.chat_messages, "session_id")

    print("[MongoDB] Indexes creation attempted (CosmosDB compatibility mode).")


def to_str_id(doc):
    """Convert a MongoDB document's _id (ObjectId) to a string 'id' field."""
    if doc and '_id' in doc:
        doc['id'] = str(doc['_id'])
    return doc
