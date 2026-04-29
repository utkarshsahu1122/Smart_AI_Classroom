import os
import time
import uuid
from io import BytesIO
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, send_file, Response
from werkzeug.utils import secure_filename
from ..services.timezone import to_local
from ..models.schemas import (
    create_quiz_session, get_quiz_session_by_code, insert_quiz_questions,
    get_questions_by_session, get_students_by_session, get_assigned_questions,
    update_quiz_session, update_student, count_assigned_questions,
)
from ..services.qr_service import generate_qr_for_session

bp = Blueprint('faculty', __name__, url_prefix='/api/faculty')

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/upload', methods=['POST'])
def upload_pdf():
    """Upload a PDF, generate vectorstore + question pool, and create a session."""
    start_time = time.time()
    print(f"Request started at: {start_time}")
    
    if 'pdf_file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'}), 400
    file = request.files['pdf_file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400
    if not file or not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Only PDF files are allowed'}), 400

    filename = secure_filename(file.filename)
    mcq_weight = int(request.form.get('mcq_weight', 70))
    fill_weight = int(request.form.get('fill_weight', 30))
    
    session_code = str(uuid.uuid4())[:8].upper()
    uploads_dir = os.path.join(current_app.root_path, 'static', 'temp_uploads')
    os.makedirs(uploads_dir, exist_ok=True)

    unique_filename = f"{session_code}_{filename}"
    file_path = os.path.join(uploads_dir, unique_filename)
    file.save(file_path)

    # Process PDF + generate entire question pool at upload time
    from ..services.rag_engine import process_pdf_and_generate_pool
    try:
        quiz_data = process_pdf_and_generate_pool(file_path, session_code)
    except Exception as e:
        print(f"[Faculty] Error during PDF processing or generation: {e}")
        try:
            os.remove(file_path)
        except OSError:
            pass
        end_time = time.time()
        print(f"Request ended at: {end_time}. Duration: {end_time - start_time:.2f}s")
        return jsonify({'success': False, 'error': 'Processing exceeded limits or failed. Please try a smaller PDF or try again later.'}), 500

    # VALIDATION: Never create a session with 0 questions
    if not quiz_data or len(quiz_data) < 5:
        try:
            os.remove(file_path)
        except OSError:
            pass
        count = len(quiz_data) if quiz_data else 0
        print(f"[Faculty] REJECTED session {session_code}: only {count} questions generated")
        return jsonify({
            'success': False,
            'error': f'Question generation failed — only {count} questions could be generated. This can happen if the PDF is too short, image-heavy, or the AI service is temporarily unavailable. Please try uploading again.'
        }), 422

    qr_path = generate_qr_for_session(session_code)

    # Create session document in MongoDB
    session_doc = create_quiz_session(
        session_code=session_code,
        pdf_filename=unique_filename,
        qr_code_path=qr_path,
        timer_minutes=10,
        mcq_weight=mcq_weight,
        fill_weight=fill_weight
    )

    # Insert questions into MongoDB
    insert_quiz_questions(session_doc["id"], quiz_data)
    print(f"[Faculty] Session {session_code} created with {len(quiz_data)} questions in pool.")

    end_time = time.time()
    print(f"Request ended at: {end_time}. Duration: {end_time - start_time:.2f}s")

    return jsonify({
        'success': True,
        'session_code': session_code,
        'qr_url': f"/static/{qr_path}" if qr_path else None,
        'questions_count': len(quiz_data),
        'pdf_filename': unique_filename
    })

@bp.route('/session/<session_code>')
def session_details(session_code):
    """Get session details including student list."""
    quiz_session = get_quiz_session_by_code(session_code)
    if not quiz_session:
        return jsonify({'success': False, 'error': 'Session not found'}), 404

    students = get_students_by_session(quiz_session["id"])
    questions = get_questions_by_session(quiz_session["id"])

    student_list = []
    for s in students:
        assigned_count = count_assigned_questions(s["id"])
        student_list.append({
            'id': s['id'],
            'roll_no': s['roll_no'],
            'name': s['name'],
            'score': s.get('score', 0),
            'total': assigned_count,
            'is_logged_in': s.get('is_logged_in', False),
            'submitted': s.get('submitted_at') is not None,
            'submitted_at': to_local(s['submitted_at']) if s.get('submitted_at') else None,
            'unfair_means': s.get('unfair_means', False),
            'warning_count': s.get('warning_count', 0),
        })

    return jsonify({
        'success': True,
        'session': {
            'session_code': quiz_session['session_code'],
            'pdf_filename': quiz_session['pdf_filename'],
            'qr_url': f"/static/{quiz_session['qr_code_path']}" if quiz_session.get('qr_code_path') else None,
            'created_at': to_local(quiz_session['created_at']),
            'timer_minutes': quiz_session.get('timer_minutes', 10),
            'is_active': quiz_session.get('is_active', True),
            'questions_count': len(questions),
        },
        'students': student_list,
    })

@bp.route('/session/<session_code>/end', methods=['POST'])
def end_session(session_code):
    """Faculty ends the session — auto-submits all pending students."""
    quiz_session = get_quiz_session_by_code(session_code)
    if not quiz_session:
        return jsonify({'success': False, 'error': 'Session not found'}), 404

    update_quiz_session(quiz_session["id"], {
        "is_active": False,
        "ended_at": datetime.utcnow(),
    })

    students = get_students_by_session(quiz_session["id"])
    auto_count = 0
    for student in students:
        if student.get("submitted_at") is None:
            assigned = get_assigned_questions(student["id"])
            score = 0
            for sq in assigned:
                if sq.get("student_answer"):
                    if sq["student_answer"].strip().lower() == sq["question"]["correct_answer"].strip().lower():
                        score += 1
            update_student(student["id"], {
                "score": score,
                "submitted_at": datetime.utcnow(),
                "is_logged_in": False,
            })
            auto_count += 1

    print(f"[Faculty] Session {session_code} ended. {auto_count} students auto-submitted.")

    return jsonify({
        'success': True,
        'auto_submitted': auto_count
    })

@bp.route('/session/<session_code>/report')
def download_report(session_code):
    """Generate and download a .csv Excel report for the quiz session."""
    import csv
    from io import StringIO

    quiz_session = get_quiz_session_by_code(session_code)
    if not quiz_session:
        return jsonify({'success': False, 'error': 'Session not found'}), 404

    students = get_students_by_session(quiz_session["id"])

    si = StringIO()
    cw = csv.writer(si)

    # --- Session Info ---
    cw.writerow(['QUIZ SESSION REPORT'])
    cw.writerow(['Session Code', quiz_session['session_code']])
    cw.writerow(['PDF Document', quiz_session['pdf_filename']])
    cw.writerow(['Created At', to_local(quiz_session['created_at'])])
    cw.writerow(['Status', 'Ended' if not quiz_session.get('is_active') else 'Active'])
    cw.writerow(['Total Students', len(students)])
    cw.writerow([])

    # --- Student Results Table ---
    cw.writerow(['S.No', 'Roll No', 'Name', 'Score', 'Total Assigned', 'Submitted At', 'Integrity Status', 'Proctor Warnings'])

    total_q = 20  # default
    if students:
        for idx, student in enumerate(students, 1):
            assigned_count = count_assigned_questions(student["id"])
            total_q = assigned_count or 20
            submitted = to_local(student['submitted_at']) if student.get('submitted_at') else 'Not Submitted'
            status = 'UNFAIR MEANS' if student.get('unfair_means') else 'Fair'

            cw.writerow([
                idx,
                student['roll_no'],
                student['name'],
                student.get('score', 0) if student.get('submitted_at') else '—',
                total_q,
                submitted,
                status,
                student.get('warning_count', 0),
            ])
    else:
        cw.writerow(['No students participated in this session.'])

    cw.writerow([])

    # --- Summary Statistics ---
    if students:
        scores = [s.get('score', 0) for s in students if s.get('submitted_at')]
        if scores:
            cw.writerow(['SUMMARY STATISTICS'])
            avg_score = sum(scores) / len(scores)
            cw.writerow(['Average Score', f"{avg_score:.1f}"])
            cw.writerow(['Highest Score', max(scores)])
            cw.writerow(['Lowest Score', min(scores)])

            pass_threshold = total_q / 2
            pass_count = sum(1 for s in scores if s >= pass_threshold)
            cw.writerow(['Pass Rate (>=50%)', f"{pass_count}/{len(scores)} ({pass_count/len(scores)*100:.0f}%)"])

    output = si.getvalue()

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=Quiz_Report_{session_code}.csv"}
    )
