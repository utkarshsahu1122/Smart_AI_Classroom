import os
import uuid
from io import BytesIO
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, send_file, url_for
from werkzeug.utils import secure_filename
from ..services.timezone import to_local
from ..models.database import db
from ..models.schemas import QuizSession, QuizQuestion, Student
from ..services.qr_service import generate_qr_for_session

bp = Blueprint('faculty', __name__, url_prefix='/api/faculty')

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/upload', methods=['POST'])
def upload_pdf():
    """Upload a PDF, generate vectorstore + question pool, and create a session."""
    if 'pdf_file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'}), 400
    file = request.files['pdf_file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400
    if not file or not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Only PDF files are allowed'}), 400

    filename = secure_filename(file.filename)
    session_code = str(uuid.uuid4())[:8].upper()
    uploads_dir = os.path.join(current_app.root_path, 'static', 'temp_uploads')
    os.makedirs(uploads_dir, exist_ok=True)

    unique_filename = f"{session_code}_{filename}"
    file_path = os.path.join(uploads_dir, unique_filename)
    file.save(file_path)

    # Process PDF + generate entire question pool at upload time
    from ..services.rag_engine import process_pdf_and_generate_pool
    quiz_data = process_pdf_and_generate_pool(file_path, session_code)

    # VALIDATION: Never create a session with 0 questions
    if not quiz_data or len(quiz_data) < 5:
        # Clean up the uploaded file
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

    new_session = QuizSession(
        session_code=session_code,
        pdf_filename=unique_filename,
        qr_code_path=qr_path,
        timer_minutes=10,
        questions_generated=True,
        is_active=True
    )
    db.session.add(new_session)
    db.session.flush()

    for q_data in quiz_data:
        q_options = "|".join(q_data.get('options', [])) if q_data.get('options') else ""
        new_q = QuizQuestion(
            session_id=new_session.id,
            question_text=q_data['question_text'],
            question_type=q_data['question_type'],
            options=q_options,
            correct_answer=q_data['correct_answer']
        )
        db.session.add(new_q)

    db.session.commit()
    print(f"[Faculty] Session {session_code} created with {len(quiz_data)} questions in pool.")

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
    quiz_session = QuizSession.query.filter_by(session_code=session_code).first()
    if not quiz_session:
        return jsonify({'success': False, 'error': 'Session not found'}), 404

    students = Student.query.filter_by(session_id=quiz_session.id).order_by(Student.roll_no).all()

    return jsonify({
        'success': True,
        'session': {
            'session_code': quiz_session.session_code,
            'pdf_filename': quiz_session.pdf_filename,
            'qr_url': f"/static/{quiz_session.qr_code_path}" if quiz_session.qr_code_path else None,
            'created_at': to_local(quiz_session.created_at),
            'timer_minutes': quiz_session.timer_minutes,
            'is_active': quiz_session.is_active,
            'questions_count': len(quiz_session.questions),
        },
        'students': [{
            'id': s.id,
            'roll_no': s.roll_no,
            'name': s.name,
            'score': s.score,
            'total': len(s.assigned_questions),
            'is_logged_in': s.is_logged_in,
            'submitted': s.submitted_at is not None,
            'submitted_at': to_local(s.submitted_at) if s.submitted_at else None,
            'unfair_means': s.unfair_means or False,
            'warning_count': s.warning_count or 0,
        } for s in students]
    })

@bp.route('/session/<session_code>/end', methods=['POST'])
def end_session(session_code):
    """Faculty ends the session — auto-submits all pending students."""
    quiz_session = QuizSession.query.filter_by(session_code=session_code).first()
    if not quiz_session:
        return jsonify({'success': False, 'error': 'Session not found'}), 404

    quiz_session.is_active = False
    quiz_session.ended_at = datetime.utcnow()

    unsubmitted = Student.query.filter_by(session_id=quiz_session.id, submitted_at=None).all()
    for student in unsubmitted:
        score = 0
        for sq in student.assigned_questions:
            if sq.student_answer:
                if sq.student_answer.strip().lower() == sq.question.correct_answer.strip().lower():
                    score += 1
        student.score = score
        student.submitted_at = datetime.utcnow()
        student.is_logged_in = False

    db.session.commit()
    print(f"[Faculty] Session {session_code} ended. {len(unsubmitted)} students auto-submitted.")

    return jsonify({
        'success': True,
        'auto_submitted': len(unsubmitted)
    })

@bp.route('/session/<session_code>/report')
def download_report(session_code):
    """Generate and download a .csv Excel report for the quiz session."""
    import csv
    from io import StringIO
    from flask import Response

    quiz_session = QuizSession.query.filter_by(session_code=session_code).first()
    if not quiz_session:
        return jsonify({'success': False, 'error': 'Session not found'}), 404

    students = Student.query.filter_by(session_id=quiz_session.id).order_by(Student.roll_no).all()

    si = StringIO()
    cw = csv.writer(si)

    # --- Session Info ---
    cw.writerow(['QUIZ SESSION REPORT'])
    cw.writerow(['Session Code', quiz_session.session_code])
    cw.writerow(['PDF Document', quiz_session.pdf_filename])
    cw.writerow(['Created At', to_local(quiz_session.created_at)])
    cw.writerow(['Status', 'Ended' if not quiz_session.is_active else 'Active'])
    cw.writerow(['Total Students', len(students)])
    cw.writerow([])  # Blank row

    # --- Student Results Table ---
    cw.writerow(['S.No', 'Roll No', 'Name', 'Score', 'Total Assigned', 'Submitted At', 'Integrity Status', 'Proctor Warnings'])

    if students:
        for idx, student in enumerate(students, 1):
            total_q = len(student.assigned_questions) or 20
            submitted = to_local(student.submitted_at) if student.submitted_at else 'Not Submitted'
            status = 'UNFAIR MEANS' if student.unfair_means else 'Fair'
            
            cw.writerow([
                idx,
                student.roll_no,
                student.name,
                student.score if student.submitted_at else '—',
                total_q,
                submitted,
                status,
                student.warning_count or 0
            ])
    else:
        cw.writerow(['No students participated in this session.'])

    cw.writerow([])  # Blank row

    # --- Summary Statistics ---
    if students:
        scores = [s.score for s in students if s.submitted_at]
        if scores:
            cw.writerow(['SUMMARY STATISTICS'])
            avg_score = sum(scores) / len(scores)
            cw.writerow(['Average Score', f"{avg_score:.1f}"])
            cw.writerow(['Highest Score', max(scores)])
            cw.writerow(['Lowest Score', min(scores)])
            
            # Assuming passing is 50% of the assigned questions
            pass_threshold = total_q / 2
            pass_count = sum(1 for s in scores if s >= pass_threshold)
            cw.writerow(['Pass Rate (>=50%)', f"{pass_count}/{len(scores)} ({pass_count/len(scores)*100:.0f}%)"])

    output = si.getvalue()
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=Quiz_Report_{session_code}.csv"}
    )
