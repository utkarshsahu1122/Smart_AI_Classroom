"""
Student Doubt Solver API — all endpoints under /api/doubt/
Protected by JWT authentication.
"""

from io import BytesIO
from flask import Blueprint, request, jsonify, send_file
from ..services.doubt_solver import (
    register_profile,
    authenticate_profile,
    process_student_pdf,
    create_chat_session,
    send_message,
    get_chat_history,
    get_session_messages,
    cleanup_expired_sessions,
)
from ..services.auth import generate_token, auth_required
from ..services.pdf_export import generate_chat_pdf
from ..models.chat import (
    get_document_by_id, get_documents_by_student,
    get_doubt_session_by_id,
)

bp = Blueprint('student_doubt', __name__, url_prefix='/api/doubt')


# ─── Auth Endpoints (Public) ──────────────────────────

@bp.route('/register', methods=['POST'])
def register():
    """Register a new student profile with password."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Invalid request'}), 400

    name = data.get('name', '').strip()
    roll_no = data.get('roll_no', '').strip()
    password = data.get('password', '')

    if not name or not roll_no or not password:
        return jsonify({'success': False, 'error': 'Name, Roll No, and Password are required'}), 400

    if len(password) < 4:
        return jsonify({'success': False, 'error': 'Password must be at least 4 characters'}), 400

    try:
        profile = register_profile(name, roll_no, password)
        token = generate_token(profile['id'], profile['roll_no'])
        return jsonify({
            'success': True,
            'token': token,
            'student_id': profile['id'],
            'name': profile['name'],
            'roll_no': profile['roll_no'],
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 409


@bp.route('/login', methods=['POST'])
def login():
    """Login with roll_no + password. Returns JWT token."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Invalid request'}), 400

    roll_no = data.get('roll_no', '').strip()
    password = data.get('password', '')

    if not roll_no or not password:
        return jsonify({'success': False, 'error': 'Roll No and Password are required'}), 400

    profile = authenticate_profile(roll_no, password)
    if not profile:
        return jsonify({'success': False, 'error': 'Invalid Roll No or Password'}), 401

    token = generate_token(profile['id'], profile['roll_no'])

    # Get their documents
    docs = get_documents_by_student(profile['id'])
    doc_list = [{
        'id': d['id'],
        'filename': d['original_filename'],
    } for d in docs]

    return jsonify({
        'success': True,
        'token': token,
        'student_id': profile['id'],
        'name': profile['name'],
        'roll_no': profile['roll_no'],
        'documents': doc_list,
    })


# ─── Protected Endpoints ──────────────────────────────

@bp.route('/upload-pdf', methods=['POST'])
@auth_required
def upload_pdf(current_student_id):
    """Upload a PDF for the doubt solver."""
    if 'pdf_file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400

    file = request.files['pdf_file']
    if file.filename == '' or not file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'error': 'Only PDF files are allowed'}), 400

    try:
        doc = process_student_pdf(current_student_id, file, file.filename)
        return jsonify({
            'success': True,
            'document_id': doc['id'],
            'filename': doc['original_filename'],
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/chat/create', methods=['POST'])
@auth_required
def create_chat(current_student_id):
    """Create a new chat session linked to a document."""
    data = request.get_json()
    document_id = data.get('document_id')

    if not document_id:
        return jsonify({'success': False, 'error': 'document_id required'}), 400

    doc = get_document_by_id(document_id)
    if not doc or doc['student_id'] != current_student_id:
        return jsonify({'success': False, 'error': 'Document not found or access denied'}), 404

    session = create_chat_session(current_student_id, document_id)

    return jsonify({
        'success': True,
        'session_id': session['id'],
        'title': session['title'],
    })


@bp.route('/chat/send', methods=['POST'])
@auth_required
def chat_send(current_student_id):
    """Send a student question and get an AI response."""
    data = request.get_json()
    session_id = data.get('session_id')
    query = data.get('query', '').strip()

    if not session_id or not query:
        return jsonify({'success': False, 'error': 'session_id and query required'}), 400

    result = send_message(session_id, query, requesting_student_id=current_student_id)

    if 'error' in result:
        return jsonify({'success': False, 'error': result['error']}), 400

    return jsonify({
        'success': True,
        'answer': result['answer'],
        'sources': result.get('sources', []),
    })


@bp.route('/chat/history')
@auth_required
def chat_history(current_student_id):
    """Get all active chat sessions for the authenticated student."""
    sessions = get_chat_history(current_student_id)
    return jsonify({'success': True, 'sessions': sessions})


@bp.route('/chat/<session_id>/messages')
@auth_required
def chat_messages(session_id, current_student_id):
    """Get all messages in a chat session (ownership enforced)."""
    result = get_session_messages(session_id, requesting_student_id=current_student_id)

    if 'error' in result:
        return jsonify({'success': False, 'error': result['error']}), 403

    return jsonify({
        'success': True,
        'messages': result['messages'],
        'title': result['title'],
        'document': result['document'],
    })


@bp.route('/chat/<session_id>/download')
@auth_required
def download_summary(session_id, current_student_id):
    """Download a PDF summary of the chat session."""
    session = get_doubt_session_by_id(session_id)
    if not session:
        return jsonify({'success': False, 'error': 'Session not found'}), 404

    if session['student_id'] != current_student_id:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    buffer = generate_chat_pdf(session)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"doubt_summary_{session_id}.pdf",
        mimetype='application/pdf',
    )


@bp.route('/documents')
@auth_required
def list_documents(current_student_id):
    """List all uploaded PDFs for the authenticated student."""
    docs = get_documents_by_student(current_student_id)

    from ..services.timezone import to_local
    return jsonify({
        'success': True,
        'documents': [{
            'id': d['id'],
            'filename': d['original_filename'],
            'uploaded_at': to_local(d['uploaded_at']),
        } for d in docs]
    })


@bp.route('/cleanup', methods=['POST'])
def cleanup():
    """Cleanup expired chat sessions."""
    count = cleanup_expired_sessions()
    return jsonify({'success': True, 'expired_sessions_cleaned': count})
