import qrcode
import os
from flask import current_app

def generate_qr_for_session(session_code):
    """Generates a QR code for a given session code to login as student"""
    # Points to React frontend — uses FRONTEND_URL env var for production
    frontend_url = os.environ.get('FRONTEND_URL', 'http://127.0.0.1:5173')
    join_url = f"{frontend_url}/student/login?session={session_code}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(join_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save QR code logic
    uploads_dir = os.path.join(current_app.root_path, 'static', 'temp_uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    
    filename = f"qr_{session_code}.png"
    filepath = os.path.join(uploads_dir, filename)
    img.save(filepath)
    
    # Returning the relative path to be stored and used in HTML
    return f"temp_uploads/{filename}"
