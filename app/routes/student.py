import random
from flask import Blueprint, request, jsonify
from ..models.database import db
from ..models.schemas import QuizSession, Student, QuizQuestion, StudentQuestion
from datetime import datetime

bp = Blueprint('student', __name__, url_prefix='/api/student')

@bp.route('/login', methods=['POST'])
def login():
    """Student login — assigns random questions from the pool."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Invalid request'}), 400

    name = data.get('name', '').strip()
    roll_no = data.get('roll_no', '').strip()
    session_code = data.get('session_code', '').strip()

    if not all([name, roll_no, session_code]):
        return jsonify({'success': False, 'error': 'Name, Roll No, and Session Code are required'}), 400

    quiz_session = QuizSession.query.filter_by(session_code=session_code).first()
    if not quiz_session:
        return jsonify({'success': False, 'error': 'Invalid Session Code'}), 404

    if not quiz_session.is_active:
        return jsonify({'success': False, 'error': 'This session has been ended by the faculty'}), 403

    if not quiz_session.questions_generated:
        return jsonify({'success': False, 'error': 'Quiz is not ready yet'}), 425

    existing_student = Student.query.filter_by(session_id=quiz_session.id, roll_no=roll_no).first()

    if existing_student:
        if existing_student.is_logged_in:
            return jsonify({'success': False, 'error': 'This Roll Number is already logged into an active quiz. Duplicate login is not allowed.'}), 409
        if existing_student.submitted_at:
            return jsonify({'success': False, 'error': 'This Roll Number has already submitted the quiz. Re-login is not permitted.'}), 409

    if not existing_student:
        student = Student(
            session_id=quiz_session.id,
            name=name,
            roll_no=roll_no,
            is_logged_in=True
        )
        db.session.add(student)
        db.session.flush()

        pool = QuizQuestion.query.filter_by(session_id=quiz_session.id).all()
        selected = random.sample(pool, min(10, len(pool)))

        for q in selected:
            sq = StudentQuestion(student_id=student.id, question_id=q.id)
            db.session.add(sq)

        db.session.commit()
        print(f"[Student] {name} ({roll_no}) assigned {len(selected)} questions instantly.")
    else:
        student = existing_student
        student.is_logged_in = True
        db.session.commit()

    return jsonify({
        'success': True,
        'student_id': student.id,
        'session_id': quiz_session.id,
        'student_name': student.name,
        'timer_minutes': quiz_session.timer_minutes,
    })

@bp.route('/quiz')
def get_quiz():
    """Get the quiz questions for a logged-in student."""
    student_id = request.args.get('student_id', type=int)
    if not student_id:
        return jsonify({'success': False, 'error': 'Missing student_id'}), 400

    student = Student.query.get(student_id)
    if not student:
        return jsonify({'success': False, 'error': 'Student not found'}), 404

    if student.submitted_at:
        return jsonify({
            'success': False,
            'error': 'Quiz already submitted',
            'already_submitted': True,
            'score': student.score,
            'total': len(student.assigned_questions)
        }), 200

    quiz_session = QuizSession.query.get(student.session_id)

    questions = []
    for sq in student.assigned_questions:
        q = sq.question
        opts = q.options.split('|') if q.options else []
        questions.append({
            'id': q.id,
            'text': q.question_text,
            'type': q.question_type,
            'options': opts,
        })

    return jsonify({
        'success': True,
        'student_name': student.name,
        'roll_no': student.roll_no,
        'timer_minutes': quiz_session.timer_minutes,
        'session_active': quiz_session.is_active,
        'questions': questions,
    })

@bp.route('/submit', methods=['POST'])
def submit_quiz():
    """Submit quiz answers and get the score."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Invalid request'}), 400

    student_id = data.get('student_id')
    answers = data.get('answers', {})

    student = Student.query.get(student_id)
    if not student:
        return jsonify({'success': False, 'error': 'Student not found'}), 404

    if student.submitted_at:
        return jsonify({
            'success': False,
            'error': 'Already submitted',
            'score': student.score,
            'total': len(student.assigned_questions)
        })

    score = 0
    total = len(student.assigned_questions)
    for sq in student.assigned_questions:
        student_answer = answers.get(str(sq.question.id), '').strip()
        sq.student_answer = student_answer
        if student_answer.lower() == sq.question.correct_answer.strip().lower():
            score += 1

    student.score = score
    student.submitted_at = datetime.utcnow()
    student.is_logged_in = False
    db.session.commit()

    return jsonify({
        'success': True,
        'score': score,
        'total': total,
        'student_name': student.name,
    })

@bp.route('/check_session')
def check_session():
    """AJAX endpoint to check if the session is still active."""
    session_id = request.args.get('session_id', type=int)
    if not session_id:
        return jsonify({'active': False})
    qs = QuizSession.query.get(session_id)
    if not qs or not qs.is_active:
        return jsonify({'active': False})
    return jsonify({'active': True})

@bp.route('/result')
def get_result():
    """Get quiz result for a student."""
    student_id = request.args.get('student_id', type=int)
    if not student_id:
        return jsonify({'success': False, 'error': 'Missing student_id'}), 400

    student = Student.query.get(student_id)
    if not student:
        return jsonify({'success': False, 'error': 'Student not found'}), 404

    return jsonify({
        'success': True,
        'name': student.name,
        'roll_no': student.roll_no,
        'score': student.score,
        'total': len(student.assigned_questions),
        'submitted': student.submitted_at is not None,
        'submitted_at': student.submitted_at.strftime('%d-%m-%Y %H:%M') if student.submitted_at else None,
    })
