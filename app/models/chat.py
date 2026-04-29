from datetime import datetime, timedelta
from .database import db

CHAT_EXPIRY_DAYS = 7


class StudentProfile(db.Model):
    """Persistent student identity for the Doubt Solver with password auth."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    roll_no = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    documents = db.relationship('StudentDocument', backref='owner', lazy=True)
    chat_sessions = db.relationship('DoubtChatSession', backref='owner', lazy=True)

    def set_password(self, password):
        import bcrypt
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, password):
        import bcrypt
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )


class StudentDocument(db.Model):
    """PDF uploaded by a student for the doubt solver."""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profile.id'), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    vectorstore_path = db.Column(db.String(500), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


class DoubtChatSession(db.Model):
    """A single conversation thread between a student and the AI doubt solver."""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profile.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('student_document.id'), nullable=True)
    title = db.Column(db.String(255), default='New Chat')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    messages = db.relationship(
        'ChatMessage', backref='chat_session', lazy=True,
        order_by='ChatMessage.created_at'
    )
    document = db.relationship('StudentDocument', lazy=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(days=CHAT_EXPIRY_DAYS)

    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at


class ChatMessage(db.Model):
    """A single message in a doubt-solving conversation."""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('doubt_chat_session.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)   # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    sources = db.Column(db.Text, nullable=True)        # JSON array of source snippets
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
