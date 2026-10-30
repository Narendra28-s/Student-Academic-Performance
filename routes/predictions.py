import json
from flask import Blueprint, jsonify, request, flash, redirect, url_for
from models import db, Student, PredictionRecord
from auth import login_required, get_current_user
from services.prediction_service import predict_student_risk, update_or_create_prediction, get_model_performance_metrics

predictions_bp = Blueprint('predictions', __name__, url_prefix='/predictions')

@predictions_bp.route('/api/student/<int:student_id>')
@login_required
def api_student_prediction(student_id):
    student = db.session.get(Student, student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404
        
    user = get_current_user()
    # Check parent permissions
    if user.role == 'parent':
        linked_ids = [l.student_id for l in user.parent_profile.children_links] if user.parent_profile else []
        if student_id not in linked_ids:
            return jsonify({'error': 'Unauthorized'}), 403
            
    # Check faculty permissions
    if user.role == 'faculty':
        assigned_class_ids = [a.class_id for a in user.faculty_profile.assignments] if user.faculty_profile else []
        if student.class_id not in assigned_class_ids:
            return jsonify({'error': 'Unauthorized'}), 403
            
    pred, details = update_or_create_prediction(student)
    return jsonify({
        'student_id': student.student_id,
        'student_name': student.full_name,
        'risk_level': pred.risk_level,
        'probability': pred.probability,
        'predicted_category': pred.predicted_category,
        'factors': details['factors'],
        'suggestions': details['suggestions'],
        'features': details['features'],
        'model_used': details['model_used'],
        'evaluated_at': pred.generated_at.strftime('%Y-%m-%d %H:%M UTC')
    })

@predictions_bp.route('/api/model-metrics')
@login_required
def api_model_metrics():
    metrics = get_model_performance_metrics()
    if not metrics:
        return jsonify({'error': 'Model metrics not available. Please train model.'}), 404
    return jsonify(metrics)
