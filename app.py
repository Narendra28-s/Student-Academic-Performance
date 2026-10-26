import os
from flask import Flask, render_template, redirect, url_for, session, g
from config import Config
from models import db, User
from auth import auth_bp, get_current_user
from routes.admin import admin_bp
from routes.faculty import faculty_bp
from routes.parent import parent_bp
from routes.predictions import predictions_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Ensure instance directory exists
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config['ML_MODEL_DIR'], exist_ok=True)
    
    # Initialize database
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(parent_bp)
    app.register_blueprint(predictions_bp)
    
    # Global context processor to make current_user available in all templates
    @app.context_processor
    def inject_user():
        return dict(current_user=get_current_user())
        
    # Root route redirection based on session / role
    @app.route('/')
    def index():
        if 'user_id' in session:
            role = session.get('user_role')
            if role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif role == 'faculty':
                return redirect(url_for('faculty.dashboard'))
            elif role == 'parent':
                return redirect(url_for('parent.dashboard'))
        return redirect(url_for('auth.login'))
        
    # Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('error.html', code=403, title="Forbidden", message="You do not have authorization to access this page."), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error.html', code=404, title="Page Not Found", message="The requested resource could not be found."), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('error.html', code=500, title="Server Error", message="An unexpected internal error occurred."), 500
        
    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # Ensure database tables exist
        db.create_all()
        # Check if database is populated; if not, print notice
        if not User.query.filter_by(email='admin@eft.edu').first():
            print("Notice: Demo database is empty. You can run 'python scripts/seed_data.py' to seed demo accounts.")
    print("\n* Starting Student Academic Performance Monitoring System...")
    print("* Local Server running at: http://127.0.0.1:5000")
    print("* Press CTRL+C to stop the server.\n")
    app.run(host='127.0.0.1', port=5000, debug=True)
