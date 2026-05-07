from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__, static_folder='static')
    import os

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'smart-classroom-secret-key-2026')

    # Enable CORS for React dev server
    CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True
)

    # Initialize MongoDB connection
    from .models.database import init_db
    init_db(app)

    # Register blueprints
    from .routes import faculty, student, student_doubt
    app.register_blueprint(faculty.bp)
    app.register_blueprint(student.bp)
    app.register_blueprint(student_doubt.bp)

    # Root Health Check for Cloud Run
    @app.route('/')
    def home():
        return {"status": "Smart Classroom API is running"}

    print("Flask app started successfully")

    return app
