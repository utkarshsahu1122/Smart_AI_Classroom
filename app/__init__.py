from flask import Flask
from flask_cors import CORS
from .models.database import db

def create_app():
    app = Flask(__name__, static_folder='static')
    import os
    
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'smart-classroom-secret-key-2026')
    
    # Deployment Database Logic
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        # SQLAlchemy 1.4+ requires postgresql:// instead of postgres://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    else:
        # Fallback to local SQLite file
        base_dir = os.path.abspath(os.path.dirname(__file__))
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, '..', 'instance', 'smart_classroom.db')
        
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

    # Serve React Frontend in Production
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        from flask import send_from_directory
        import os
        dist_dir = os.path.abspath(os.path.join(app.root_path, '..', 'frontend', 'dist'))
        if path != "" and os.path.exists(os.path.join(dist_dir, path)):
            return send_from_directory(dist_dir, path)
        else:
            # SPA fallback: always serve index.html for unknown frontend routes
            return send_from_directory(dist_dir, 'index.html')

    return app
