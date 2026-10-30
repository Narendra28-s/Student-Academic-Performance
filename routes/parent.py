from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Student, ParentProfile, ParentStudent, Mark, Attendance, FacultyFeedback, PredictionRecord
from auth import login_required, role_required, get_current_user
from services.analytics import get_parent_dashboard_metrics

parent_bp = Blueprint('parent', __name__, url_prefix='/parent')

@parent_bp.before_request
@login_required
@role_required('parent')
def enforce_parent_access():
    pass

def get_current_parent_profile():
    user = get_current_user()
    if not user or not user.parent_profile:
        return None
    return user.parent_profile

def verify_parent_child_link(parent_profile, student_id):
    """Verifies that the student is actually linked to this parent."""
    link = ParentStudent.query.filter_by(
        parent_id=parent_profile.id,
        student_id=student_id
    ).first()
    return link is not None

# ==========================================
# 1. PARENT DASHBOARD
# ==========================================
@parent_bp.route('/dashboard')
def dashboard():
    profile = get_current_parent_profile()
    if not profile:
        flash('Parent profile not linked to this user account.', 'danger')
        return redirect(url_for('auth.login'))
        
    # Get active child from query arg or session
    child_id = request.args.get('child_id')
    if child_id:
        session['active_child_id'] = int(child_id)
    else:
        child_id = session.get('active_child_id')
        
    metrics = get_parent_dashboard_metrics(profile.id, selected_student_id=child_id)
    
    if not metrics or not metrics.get('selected_student'):
        return render_template('parent/no_child.html', parent=profile)
        
    session['active_child_id'] = metrics['selected_student'].id
    return render_template('parent/dashboard.html', data=metrics)

# ==========================================
# 2. CHILD ATTENDANCE DETAILS
# ==========================================
@parent_bp.route('/attendance')
def attendance():
    profile = get_current_parent_profile()
    child_id = session.get('active_child_id') or request.args.get('child_id')
    
    if not child_id or not verify_parent_child_link(profile, int(child_id)):
        # Default to first linked child
        links = profile.children_links
        if not links:
            flash('No child associated with your account.', 'warning')
            return redirect(url_for('parent.dashboard'))
        child_id = links[0].student_id
        session['active_child_id'] = child_id
        
    student = db.session.get(Student, int(child_id))
    records = Attendance.query.filter_by(student_id=student.id).order_by(Attendance.date.desc()).all()
    stats = student.get_attendance_stats()
    
    return render_template(
        'parent/attendance.html',
        student=student,
        records=records,
        stats=stats,
        children=[l.student for l in profile.children_links]
    )

# ==========================================
# 3. CHILD ACADEMIC MARKS & HISTORY
# ==========================================
@parent_bp.route('/marks')
def marks():
    profile = get_current_parent_profile()
    child_id = session.get('active_child_id') or request.args.get('child_id')
    
    if not child_id or not verify_parent_child_link(profile, int(child_id)):
        links = profile.children_links
        if not links:
            flash('No child associated with your account.', 'warning')
            return redirect(url_for('parent.dashboard'))
        child_id = links[0].student_id
        session['active_child_id'] = child_id
        
    student = db.session.get(Student, int(child_id))
    marks_records = Mark.query.filter_by(student_id=student.id).join(Mark.assessment).order_by(Mark.updated_at.desc()).all()
    subject_perf = student.get_subject_performance()
    
    return render_template(
        'parent/marks.html',
        student=student,
        marks=marks_records,
        subject_perf=subject_perf,
        children=[l.student for l in profile.children_links]
    )

# ==========================================
# 4. TEACHER FEEDBACK & SUGGESTIONS
# ==========================================
@parent_bp.route('/feedback')
def feedback():
    profile = get_current_parent_profile()
    child_id = session.get('active_child_id') or request.args.get('child_id')
    
    if not child_id or not verify_parent_child_link(profile, int(child_id)):
        links = profile.children_links
        if not links:
            flash('No child associated with your account.', 'warning')
            return redirect(url_for('parent.dashboard'))
        child_id = links[0].student_id
        session['active_child_id'] = child_id
        
    student = db.session.get(Student, int(child_id))
    feedbacks = FacultyFeedback.query.filter_by(student_id=student.id).order_by(FacultyFeedback.created_at.desc()).all()
    
    return render_template(
        'parent/feedback.html',
        student=student,
        feedbacks=feedbacks,
        children=[l.student for l in profile.children_links]
    )
