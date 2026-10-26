import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'eft-academic-perf-secret-key-2025-prod-local')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'student_academic.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session security
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Machine Learning configuration
    ML_MODEL_DIR = os.path.join(BASE_DIR, 'ml', 'saved_models')
    ML_MODEL_PATH = os.path.join(ML_MODEL_DIR, 'academic_risk_model.joblib')
    
    # Academic Thresholds
    ATTENDANCE_WARNING_THRESHOLD = 75.0  # Percentage
    ATTENDANCE_CRITICAL_THRESHOLD = 65.0
    MARKS_PASS_THRESHOLD = 50.0  # Percentage
    MARKS_HONORS_THRESHOLD = 75.0
