from flask import Flask
from flask_cors import CORS
from .models.database import db

def create_app():
    app = Flask(__name__, static_folder='static')
    app.config['SECRET_KEY'] = 'smart-classroom-secret-key-2026'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smart_classroom.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Enable CORS for React dev server
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(app)

    with app.app_context():
        from .routes import faculty, student, student_doubt
        # Import models so SQLAlchemy creates all tables
        from .models import schemas, chat

        app.register_blueprint(faculty.bp)
        app.register_blueprint(student.bp)
        app.register_blueprint(student_doubt.bp)

        db.create_all()

    return app
