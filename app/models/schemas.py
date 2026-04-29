from datetime import datetime
from .database import db

class QuizSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_code = db.Column(db.String(50), unique=True, nullable=False)
    pdf_filename = db.Column(db.String(255), nullable=False)
    qr_code_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    timer_minutes = db.Column(db.Integer, default=10)
    questions_generated = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)       # Faculty can end this
    ended_at = db.Column(db.DateTime, nullable=True)

    students = db.relationship('Student', backref='quiz_session', lazy=True)
    questions = db.relationship('QuizQuestion', backref='quiz_session', lazy=True)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('quiz_session.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    roll_no = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, default=0)
    submitted_at = db.Column(db.DateTime, nullable=True)
    is_logged_in = db.Column(db.Boolean, default=False)   # Prevents credential reuse

    # Proctoring fields
    warning_count = db.Column(db.Integer, default=0)
    unfair_means = db.Column(db.Boolean, default=False)
    submission_reason = db.Column(db.String(50), default='manual')  # manual, time_up, session_ended, proctoring

    assigned_questions = db.relationship('StudentQuestion', backref='student', lazy=True)

class QuizQuestion(db.Model):
    """Pool of questions generated from the PDF at upload time (belongs to session, not student)."""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('quiz_session.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # 'mcq' or 'fill_blank'
    options = db.Column(db.Text, nullable=True)  # Pipe-separated options for MCQ
    correct_answer = db.Column(db.String(255), nullable=False)

class StudentQuestion(db.Model):
    """Links a student to their randomly assigned subset of questions from the pool."""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('quiz_question.id'), nullable=False)
    student_answer = db.Column(db.String(255), nullable=True)

    question = db.relationship('QuizQuestion', lazy=True)
