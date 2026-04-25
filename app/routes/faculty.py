import os
import uuid
from io import BytesIO
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, send_file, url_for
from werkzeug.utils import secure_filename
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

    qr_path = generate_qr_for_session(session_code)

    new_session = QuizSession(
        session_code=session_code,
        pdf_filename=unique_filename,
        qr_code_path=qr_path,
        timer_minutes=10,
        questions_generated=bool(quiz_data),
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
            'created_at': quiz_session.created_at.strftime('%d-%m-%Y %H:%M'),
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
            'submitted_at': s.submitted_at.strftime('%d-%m-%Y %H:%M') if s.submitted_at else None,
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
    """Generate and download a .docx Word report for the quiz session."""
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT

    quiz_session = QuizSession.query.filter_by(session_code=session_code).first()
    if not quiz_session:
        return jsonify({'success': False, 'error': 'Session not found'}), 404

    students = Student.query.filter_by(session_id=quiz_session.id).order_by(Student.roll_no).all()

    doc = Document()

    title = doc.add_heading('Quiz Session Report', level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_heading('Session Information', level=2)
    info_table = doc.add_table(rows=5, cols=2, style='Light Shading Accent 1')
    info_data = [
        ('Session Code', quiz_session.session_code),
        ('PDF Document', quiz_session.pdf_filename),
        ('Created', quiz_session.created_at.strftime('%d-%m-%Y %H:%M')),
        ('Status', 'Ended' if not quiz_session.is_active else 'Active'),
        ('Total Students', str(len(students))),
    ]
    for i, (label, value) in enumerate(info_data):
        info_table.rows[i].cells[0].text = label
        info_table.rows[i].cells[1].text = value
        for cell in info_table.rows[i].cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(11)

    doc.add_paragraph('')

    doc.add_heading('Student Results', level=2)

    if students:
        result_table = doc.add_table(rows=1, cols=5, style='Medium Shading 1 Accent 1')
        result_table.alignment = WD_TABLE_ALIGNMENT.CENTER

        headers = ['S.No', 'Roll No', 'Name', 'Score', 'Submitted At']
        for i, header in enumerate(headers):
            cell = result_table.rows[0].cells[i]
            cell.text = header
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.bold = True
                    run.font.size = Pt(11)
                    run.font.color.rgb = RGBColor(255, 255, 255)

        for idx, student in enumerate(students, 1):
            row = result_table.add_row()
            total_q = len(student.assigned_questions) or 10
            submitted = student.submitted_at.strftime('%d-%m-%Y %H:%M') if student.submitted_at else 'Not Submitted'
            values = [str(idx), student.roll_no, student.name, f"{student.score}/{total_q}", submitted]
            for i, val in enumerate(values):
                cell = row.cells[i]
                cell.text = val
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(10)
    else:
        doc.add_paragraph('No students participated in this session.', style='Intense Quote')

    doc.add_paragraph('')

    if students:
        scores = [s.score for s in students if s.submitted_at]
        if scores:
            doc.add_heading('Summary Statistics', level=2)
            total_q = 10
            stats_para = doc.add_paragraph()
            stats_para.add_run('Average Score: ').bold = True
            stats_para.add_run(f'{sum(scores)/len(scores):.1f}/{total_q}\n')
            stats_para.add_run('Highest Score: ').bold = True
            stats_para.add_run(f'{max(scores)}/{total_q}\n')
            stats_para.add_run('Lowest Score: ').bold = True
            stats_para.add_run(f'{min(scores)}/{total_q}\n')
            stats_para.add_run('Pass Rate (≥5): ').bold = True
            pass_count = sum(1 for s in scores if s >= 5)
            stats_para.add_run(f'{pass_count}/{len(scores)} ({pass_count/len(scores)*100:.0f}%)')

    doc.add_paragraph('')
    footer = doc.add_paragraph(f'Report generated on {datetime.utcnow().strftime("%d-%m-%Y %H:%M")} UTC')
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for run in footer.runs:
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(150, 150, 150)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    filename = f"Quiz_Report_{session_code}.docx"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
