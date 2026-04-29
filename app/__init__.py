from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__, static_folder='static')
    import os

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'smart-classroom-secret-key-2026')

    # Enable CORS for React dev server
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize MongoDB connection
    from .models.database import init_db
    init_db(app)

    # Register blueprints
    from .routes import faculty, student, student_doubt
    app.register_blueprint(faculty.bp)
    app.register_blueprint(student.bp)
    app.register_blueprint(student_doubt.bp)

    # Serve React Frontend in Production
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        from flask import send_from_directory
        dist_dir = os.path.abspath(os.path.join(app.root_path, '..', 'frontend', 'dist'))
        if path != "" and os.path.exists(os.path.join(dist_dir, path)):
            return send_from_directory(dist_dir, path)
        else:
            # SPA fallback: always serve index.html for unknown frontend routes
            return send_from_directory(dist_dir, 'index.html')

    return app
