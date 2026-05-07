import random
from flask import Blueprint, request, jsonify
from ..models.schemas import (
    get_quiz_session_by_code, get_quiz_session_by_id,
    get_student_by_session_and_roll, get_student_by_id,
    create_student, get_questions_by_session,
    assign_questions_to_student, get_assigned_questions,
    update_student, update_student_answer, count_assigned_questions,
)
from ..services.timezone import to_local
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

    quiz_session = get_quiz_session_by_code(session_code)
    if not quiz_session:
        return jsonify({'success': False, 'error': 'Invalid Session Code'}), 404

    if not quiz_session.get('is_active'):
        return jsonify({'success': False, 'error': 'This session has been ended by the faculty'}), 403

    if not quiz_session.get('questions_generated'):
        return jsonify({'success': False, 'error': 'Quiz is not ready yet'}), 425

    existing_student = get_student_by_session_and_roll(quiz_session["id"], roll_no)

    if existing_student:
        if existing_student.get('is_logged_in'):
            return jsonify({'success': False, 'error': 'This Roll Number is already logged into an active quiz. Duplicate login is not allowed.'}), 409
        if existing_student.get('submitted_at'):
            return jsonify({'success': False, 'error': 'This Roll Number has already submitted the quiz. Re-login is not permitted.'}), 409

    if not existing_student:
        student = create_student(quiz_session["id"], name, roll_no)

        pool = get_questions_by_session(quiz_session["id"])

        # Split pool into question types
        mcqs = [q for q in pool if q['question_type'] == 'mcq']
        fills = [q for q in pool if q['question_type'] == 'fill_blank']

        # Get weights from session (fallback to 70/30 if not present)
        mcq_weight = quiz_session.get('mcq_weight', 70)
        fill_weight = quiz_session.get('fill_weight', 30)

        # Calculate target counts based on weightage for a 20 question quiz
        total_target = min(20, len(pool))
        target_mcq = min(len(mcqs), int(total_target * (mcq_weight / 100.0)))
        target_fill = min(len(fills), total_target - target_mcq)

        # If we couldn't get enough fill_blanks, make up the difference with more MCQs (and vice-versa)
        if target_mcq + target_fill < total_target:
            target_mcq = min(len(mcqs), total_target - target_fill)
        if target_mcq + target_fill < total_target:
            target_fill = min(len(fills), total_target - target_mcq)

        selected_mcqs = random.sample(mcqs, target_mcq)
        selected_fills = random.sample(fills, target_fill)

        selected = selected_mcqs + selected_fills
        random.shuffle(selected)  # Mix them up!

        question_ids = [q["id"] for q in selected]
        assign_questions_to_student(student["id"], question_ids)

        print(f"[Student] {name} ({roll_no}) assigned {len(selected)} questions instantly.")
    else:
        student = existing_student
        update_student(student["id"], {"is_logged_in": True})

    return jsonify({
        'success': True,
        'student_id': student["id"],
        'session_id': quiz_session["id"],
        'student_name': student['name'],
        'timer_minutes': quiz_session.get('timer_minutes', 10),
    })

@bp.route('/quiz')
def get_quiz():
    """Get the quiz questions for a logged-in student."""
    student_id = request.args.get('student_id')
    if not student_id:
        return jsonify({'success': False, 'error': 'Missing student_id'}), 400

    student = get_student_by_id(student_id)
    if not student:
        return jsonify({'success': False, 'error': 'Student not found'}), 404

    assigned = get_assigned_questions(student_id)

    if student.get('submitted_at'):
        return jsonify({
            'success': False,
            'error': 'Quiz already submitted',
            'already_submitted': True,
            'score': student.get('score', 0),
            'total': len(assigned),
        }), 200

    quiz_session = get_quiz_session_by_id(student['session_id'])

    questions = []
    for sq in assigned:
        q = sq["question"]
        opts = q['options'].split('|') if q.get('options') else []
        questions.append({
            'id': q['id'],
            'text': q['question_text'],
            'type': q['question_type'],
            'options': opts,
        })

    return jsonify({
        'success': True,
        'student_name': student['name'],
        'roll_no': student['roll_no'],
        'timer_minutes': quiz_session.get('timer_minutes', 10),
        'session_active': quiz_session.get('is_active', True),
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
    reason = data.get('reason', 'manual')

    student = get_student_by_id(student_id)
    if not student:
        return jsonify({'success': False, 'error': 'Student not found'}), 404

    if student.get('submitted_at'):
        assigned = get_assigned_questions(student_id)
        return jsonify({
            'success': False,
            'error': 'Already submitted',
            'score': student.get('score', 0),
            'total': len(assigned),
        })

    assigned = get_assigned_questions(student_id)
    score = 0
    total = len(assigned)

    for sq in assigned:
        q = sq["question"]
        student_answer = answers.get(str(q['id']), '').strip()
        update_student_answer(student_id, sq["question_id"], student_answer)
        if student_answer.lower() == q['correct_answer'].strip().lower():
            score += 1

    updates = {
        "score": score,
        "submitted_at": datetime.utcnow(),
        "is_logged_in": False,
        "submission_reason": reason,
    }

    # Mark unfair means if submitted due to proctoring violations
    if reason == 'proctoring':
        updates["unfair_means"] = True

    update_student(student_id, updates)

    return jsonify({
        'success': True,
        'score': score,
        'total': total,
        'student_name': student['name'],
    })

@bp.route('/proctor/warn', methods=['POST'])
def proctor_warning():
    """Record a proctoring warning for a student."""
    data = request.get_json()
    student_id = data.get('student_id')
    reason = data.get('reason', 'unknown')

    student = get_student_by_id(student_id)
    if not student:
        return jsonify({'success': False, 'error': 'Student not found'}), 404

    new_count = (student.get('warning_count') or 0) + 1
    update_student(student_id, {"warning_count": new_count})

    print(f"[Proctor] Warning {new_count} for {student['name']} ({student['roll_no']}): {reason}")

    should_auto_submit = new_count >= 2

    return jsonify({
        'success': True,
        'warning_count': new_count,
        'auto_submit': should_auto_submit,
    })

@bp.route('/check_session')
def check_session():
    """AJAX endpoint to check if the session is still active."""
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'active': False})
    qs = get_quiz_session_by_id(session_id)
    if not qs or not qs.get('is_active'):
        return jsonify({'active': False})
    return jsonify({'active': True})

@bp.route('/result')
def get_result():
    """Get quiz result for a student."""
    student_id = request.args.get('student_id')
    if not student_id:
        return jsonify({'success': False, 'error': 'Missing student_id'}), 400

    student = get_student_by_id(student_id)
    if not student:
        return jsonify({'success': False, 'error': 'Student not found'}), 404

    assigned_count = count_assigned_questions(student_id)

    return jsonify({
        'success': True,
        'name': student['name'],
        'roll_no': student['roll_no'],
        'score': student.get('score', 0),
        'total': assigned_count,
        'submitted': student.get('submitted_at') is not None,
        'submitted_at': to_local(student['submitted_at']) if student.get('submitted_at') else None,
        'unfair_means': student.get('unfair_means', False),
        'warning_count': student.get('warning_count', 0),
        'submission_reason': student.get('submission_reason', 'manual'),
    })
