import io
import csv
from datetime import datetime, date, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, session
from models import (
    db, Student, AcademicClass, FacultyProfile, FacultyClass,
    Subject, Assessment, Mark, Attendance, FacultyFeedback,
    PredictionRecord
)
from auth import login_required, role_required, get_current_user
from services.analytics import get_faculty_dashboard_metrics
from services.prediction_service import update_or_create_prediction

faculty_bp = Blueprint('faculty', __name__, url_prefix='/faculty')

@faculty_bp.before_request
@login_required
@role_required('faculty')
def enforce_faculty_access():
    pass

def get_current_faculty_profile():
    user = get_current_user()
    if not user or not user.faculty_profile:
        return None
    return user.faculty_profile

def get_faculty_assigned_ids(profile):
    class_ids = [a.class_id for a in profile.assignments]
    subject_ids = [a.subject_id for a in profile.assignments]
    return list(set(class_ids)), list(set(subject_ids))

# ==========================================
# 1. FACULTY DASHBOARD
# ==========================================
@faculty_bp.route('/dashboard')
def dashboard():
    profile = get_current_faculty_profile()
    if not profile:
        flash('Faculty profile not linked to this user account.', 'danger')
        return redirect(url_for('auth.login'))
        
    metrics = get_faculty_dashboard_metrics(profile.id)
    return render_template('faculty/dashboard.html', metrics=metrics)

# ==========================================
# 2. ASSIGNED STUDENTS & PERFORMANCE VIEW
# ==========================================
@faculty_bp.route('/students')
def students():
    profile = get_current_faculty_profile()
    class_ids, _ = get_faculty_assigned_ids(profile)
    
    selected_class = request.args.get('class_id', '')
    search = request.args.get('q', '').strip()
    
    query = Student.query.filter(Student.class_id.in_(class_ids)) if class_ids else Student.query.filter(False)
    
    if selected_class:
        query = query.filter_by(class_id=int(selected_class))
    if search:
        query = query.filter(
            (Student.first_name.ilike(f'%{search}%')) |
            (Student.last_name.ilike(f'%{search}%')) |
            (Student.student_id.ilike(f'%{search}%'))
        )
        
    students_list = query.order_by(Student.student_id).all()
    assigned_classes = AcademicClass.query.filter(AcademicClass.id.in_(class_ids)).all() if class_ids else []
    
    return render_template(
        'faculty/students.html',
        students=students_list,
        classes=assigned_classes,
        selected_class=selected_class,
        search_query=search
    )

@faculty_bp.route('/students/<int:id>')
def student_detail(id):
    profile = get_current_faculty_profile()
    class_ids, subject_ids = get_faculty_assigned_ids(profile)
    
    student = db.session.get(Student, id)
    if not student or (student.class_id not in class_ids):
        flash('Student not found or not in your assigned classes.', 'danger')
        return redirect(url_for('faculty.students'))
        
    # Re-evaluate latest prediction
    pred, pred_details = update_or_create_prediction(student)
    
    # Marks only for assigned subjects or all assessments for context
    marks = Mark.query.filter_by(student_id=student.id).join(Assessment).order_by(Assessment.date.desc()).all()
    attendance = Attendance.query.filter_by(student_id=student.id).order_by(Attendance.date.desc()).all()
    feedbacks = FacultyFeedback.query.filter_by(student_id=student.id).order_by(FacultyFeedback.created_at.desc()).all()
    
    assigned_subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all() if subject_ids else []
    
    return render_template(
        'faculty/student_detail.html',
        student=student,
        marks=marks,
        attendance=attendance,
        feedbacks=feedbacks,
        prediction=pred,
        pred_details=pred_details,
        assigned_subjects=assigned_subjects
    )

# ==========================================
# 3. MARKS MANAGEMENT (Entry & Validation)
# ==========================================
@faculty_bp.route('/marks')
def marks_list():
    profile = get_current_faculty_profile()
    class_ids, subject_ids = get_faculty_assigned_ids(profile)
    
    selected_class = request.args.get('class_id', '')
    selected_subject = request.args.get('subject_id', '')
    
    query = Mark.query.join(Assessment).filter(
        Assessment.class_id.in_(class_ids),
        Assessment.subject_id.in_(subject_ids)
    )
    
    if selected_class:
        query = query.filter(Assessment.class_id == int(selected_class))
    if selected_subject:
        query = query.filter(Assessment.subject_id == int(selected_subject))
        
    marks = query.order_by(Assessment.date.desc()).all()
    assigned_classes = AcademicClass.query.filter(AcademicClass.id.in_(class_ids)).all() if class_ids else []
    assigned_subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all() if subject_ids else []
    
    return render_template(
        'faculty/marks.html',
        marks=marks,
        classes=assigned_classes,
        subjects=assigned_subjects,
        selected_class=selected_class,
        selected_subject=selected_subject
    )

@faculty_bp.route('/marks/entry', methods=['GET', 'POST'])
def marks_entry():
    profile = get_current_faculty_profile()
    class_ids, subject_ids = get_faculty_assigned_ids(profile)
    
    assigned_classes = AcademicClass.query.filter(AcademicClass.id.in_(class_ids)).all() if class_ids else []
    assigned_subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all() if subject_ids else []
    
    selected_class_id = request.args.get('class_id') or (assigned_classes[0].id if assigned_classes else None)
    selected_subject_id = request.args.get('subject_id') or (assigned_subjects[0].id if assigned_subjects else None)
    
    # Available assessments for selected class & subject
    assessments = []
    if selected_class_id and selected_subject_id:
        assessments = Assessment.query.filter_by(
            class_id=int(selected_class_id),
            subject_id=int(selected_subject_id)
        ).order_by(Assessment.date.desc()).all()
        
    selected_assessment_id = request.args.get('assessment_id') or (assessments[0].id if assessments else None)
    selected_assessment = db.session.get(Assessment, int(selected_assessment_id)) if selected_assessment_id else None
    
    # Students in selected class
    students_in_class = []
    current_marks_map = {}
    if selected_class_id:
        students_in_class = Student.query.filter_by(class_id=int(selected_class_id)).order_by(Student.student_id).all()
        if selected_assessment:
            marks = Mark.query.filter_by(assessment_id=selected_assessment.id).all()
            for m in marks:
                current_marks_map[m.student_id] = m
                
    if request.method == 'POST':
        post_assessment_id = request.form.get('assessment_id')
        assessment_obj = db.session.get(Assessment, int(post_assessment_id)) if post_assessment_id else None
        
        if not assessment_obj:
            flash('Invalid assessment selected.', 'danger')
            return redirect(request.url)
            
        max_marks = assessment_obj.max_marks
        saved_count = 0
        error_count = 0
        
        # Iterate over form fields: mark_<student_id>, remarks_<student_id>
        for key, val in request.form.items():
            if key.startswith('score_'):
                student_id = int(key.split('_')[1])
                score_str = val.strip()
                remarks = request.form.get(f'remarks_{student_id}', '').strip()
                
                if score_str != '':
                    try:
                        score_val = float(score_str)
                        if score_val < 0 or score_val > max_marks:
                            flash(f'Score for Student ID {student_id} must be between 0 and {max_marks}. Record skipped.', 'warning')
                            error_count += 1
                            continue
                            
                        # Check existing mark
                        mark_record = Mark.query.filter_by(student_id=student_id, assessment_id=assessment_obj.id).first()
                        if mark_record:
                            mark_record.score = score_val
                            mark_record.remarks = remarks
                            mark_record.recorded_by = get_current_user().id
                        else:
                            mark_record = Mark(
                                student_id=student_id,
                                assessment_id=assessment_obj.id,
                                score=score_val,
                                remarks=remarks,
                                recorded_by=get_current_user().id
                            )
                            db.session.add(mark_record)
                        saved_count += 1
                    except ValueError:
                        error_count += 1
                        
        db.session.commit()
        
        # Update ML predictions for students in this class
        for s in students_in_class:
            update_or_create_prediction(s)
            
        flash(f'Saved marks for {saved_count} students in "{assessment_obj.name}".', 'success')
        return redirect(url_for('faculty.marks_entry', class_id=selected_class_id, subject_id=selected_subject_id, assessment_id=assessment_obj.id))

    return render_template(
        'faculty/marks_entry.html',
        classes=assigned_classes,
        subjects=assigned_subjects,
        assessments=assessments,
        selected_class_id=int(selected_class_id) if selected_class_id else None,
        selected_subject_id=int(selected_subject_id) if selected_subject_id else None,
        selected_assessment=selected_assessment,
        students=students_in_class,
        current_marks=current_marks_map
    )

# ==========================================
# 4. ASSESSMENTS CREATION
# ==========================================
@faculty_bp.route('/assessments/new', methods=['POST'])
def create_assessment():
    profile = get_current_faculty_profile()
    class_ids, subject_ids = get_faculty_assigned_ids(profile)
    
    class_id = request.form.get('class_id')
    subject_id = request.form.get('subject_id')
    name = request.form.get('name', '').strip()
    assessment_type = request.form.get('assessment_type', 'Internal Test')
    max_marks = request.form.get('max_marks', 100.0)
    weightage = request.form.get('weightage', 20.0)
    assess_date_str = request.form.get('date', '')
    
    if not class_id or not subject_id or not name:
        flash('Class, Subject, and Assessment Title are required.', 'danger')
        return redirect(url_for('faculty.marks_entry'))
        
    if int(class_id) not in class_ids or int(subject_id) not in subject_ids:
        flash('You are not authorized to create assessments for this class/subject.', 'danger')
        return redirect(url_for('faculty.marks_entry'))
        
    try:
        assess_date = datetime.strptime(assess_date_str, '%Y-%m-%d').date() if assess_date_str else date.today()
        assessment = Assessment(
            name=name,
            assessment_type=assessment_type,
            max_marks=float(max_marks),
            weightage=float(weightage),
            class_id=int(class_id),
            subject_id=int(subject_id),
            date=assess_date
        )
        db.session.add(assessment)
        db.session.commit()
        flash(f'Assessment "{name}" created successfully. You can now enter marks.', 'success')
        return redirect(url_for('faculty.marks_entry', class_id=class_id, subject_id=subject_id, assessment_id=assessment.id))
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to create assessment: {str(e)}', 'danger')
        return redirect(url_for('faculty.marks_entry'))

# ==========================================
# 5. ATTENDANCE MANAGEMENT (Daily Batch Entry)
# ==========================================
@faculty_bp.route('/attendance')
def attendance_list():
    profile = get_current_faculty_profile()
    class_ids, _ = get_faculty_assigned_ids(profile)
    
    assigned_classes = AcademicClass.query.filter(AcademicClass.id.in_(class_ids)).all() if class_ids else []
    selected_class = request.args.get('class_id') or (assigned_classes[0].id if assigned_classes else None)
    selected_date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    
    records = []
    if selected_class:
        try:
            sel_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            records = Attendance.query.filter_by(
                class_id=int(selected_class),
                date=sel_date
            ).all()
        except ValueError:
            pass
            
    return render_template(
        'faculty/attendance.html',
        classes=assigned_classes,
        selected_class=int(selected_class) if selected_class else None,
        selected_date=selected_date_str,
        records=records
    )

@faculty_bp.route('/attendance/entry', methods=['GET', 'POST'])
def attendance_entry():
    profile = get_current_faculty_profile()
    class_ids, _ = get_faculty_assigned_ids(profile)
    
    assigned_classes = AcademicClass.query.filter(AcademicClass.id.in_(class_ids)).all() if class_ids else []
    selected_class_id = request.args.get('class_id') or (assigned_classes[0].id if assigned_classes else None)
    selected_date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    
    try:
        att_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        att_date = date.today()
        
    students = []
    current_records = {}
    if selected_class_id:
        students = Student.query.filter_by(class_id=int(selected_class_id)).order_by(Student.student_id).all()
        existing = Attendance.query.filter_by(class_id=int(selected_class_id), date=att_date).all()
        for r in existing:
            current_records[r.student_id] = r
            
    if request.method == 'POST':
        post_class_id = int(request.form.get('class_id'))
        post_date_str = request.form.get('date')
        try:
            post_date = datetime.strptime(post_date_str, '%Y-%m-%d').date()
        except ValueError:
            post_date = date.today()
            
        saved = 0
        for s in students:
            status = request.form.get(f'status_{s.id}', 'Present')
            remarks = request.form.get(f'remarks_{s.id}', '').strip()
            
            # Check existing for (student_id, date) to prevent duplicates
            rec = Attendance.query.filter_by(student_id=s.id, date=post_date).first()
            if rec:
                rec.status = status
                rec.remarks = remarks
                rec.recorded_by = get_current_user().id
            else:
                rec = Attendance(
                    student_id=s.id,
                    class_id=post_class_id,
                    date=post_date,
                    status=status,
                    remarks=remarks,
                    recorded_by=get_current_user().id
                )
                db.session.add(rec)
            saved += 1
            
        db.session.commit()
        
        # Update predictions
        for s in students:
            update_or_create_prediction(s)
            
        flash(f'Attendance successfully recorded for {saved} students on {post_date}.', 'success')
        return redirect(url_for('faculty.attendance_entry', class_id=post_class_id, date=post_date.strftime('%Y-%m-%d')))
        
    return render_template(
        'faculty/attendance_entry.html',
        classes=assigned_classes,
        selected_class_id=int(selected_class_id) if selected_class_id else None,
        selected_date=att_date.strftime('%Y-%m-%d'),
        students=students,
        current_records=current_records
    )

# ==========================================
# 6. FACULTY FEEDBACK & IMPROVEMENT SUGGESTIONS
# ==========================================
@faculty_bp.route('/feedback/add', methods=['POST'])
def add_feedback():
    profile = get_current_faculty_profile()
    student_id = request.form.get('student_id')
    subject_id = request.form.get('subject_id')
    feedback_text = request.form.get('feedback_text', '').strip()
    recommendation = request.form.get('recommendation', '').strip()
    
    if not student_id or not feedback_text:
        flash('Feedback text cannot be empty.', 'danger')
        return redirect(request.referrer or url_for('faculty.dashboard'))
        
    try:
        fb = FacultyFeedback(
            student_id=int(student_id),
            faculty_id=profile.id,
            subject_id=int(subject_id) if subject_id else None,
            feedback_text=feedback_text,
            recommendation=recommendation,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(fb)
        db.session.commit()
        flash('Academic feedback submitted. It will be visible to student and parent.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving feedback: {str(e)}', 'danger')
        
    return redirect(request.referrer or url_for('faculty.student_detail', id=student_id))

# ==========================================
# 7. FACULTY PREDICTIONS & AT-RISK MONITORING
# ==========================================
@faculty_bp.route('/predictions')
def predictions():
    profile = get_current_faculty_profile()
    class_ids, _ = get_faculty_assigned_ids(profile)
    
    students = Student.query.filter(Student.class_id.in_(class_ids)).all() if class_ids else []
    assigned_classes = AcademicClass.query.filter(AcademicClass.id.in_(class_ids)).all() if class_ids else []
    
    # Calculate fresh predictions
    predictions_data = []
    for s in students:
        p = s.get_latest_prediction()
        if not p:
            p, _ = update_or_create_prediction(s)
        predictions_data.append({
            'student': s,
            'prediction': p,
            'avg_marks': s.get_average_marks(),
            'attendance_pct': s.get_attendance_percentage()
        })
        
    predictions_data.sort(key=lambda x: (x['prediction'].risk_level != 'High', x['prediction'].risk_level != 'Medium', x['avg_marks']))
    
    return render_template(
        'faculty/predictions.html',
        predictions_data=predictions_data,
        classes=assigned_classes
    )

# ==========================================
# 8. CSV EXPORT FOR FACULTY
# ==========================================
@faculty_bp.route('/export/marks')
def export_marks():
    profile = get_current_faculty_profile()
    class_ids, subject_ids = get_faculty_assigned_ids(profile)
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Student ID', 'Student Name', 'Class', 'Subject',
        'Assessment', 'Score', 'Max Marks', 'Percentage %', 'Remarks'
    ])
    
    marks = Mark.query.join(Assessment).filter(
        Assessment.class_id.in_(class_ids),
        Assessment.subject_id.in_(subject_ids)
    ).all()
    
    for m in marks:
        writer.writerow([
            m.student.student_id,
            m.student.full_name,
            m.assessment.academic_class.display_name,
            m.assessment.subject.name,
            m.assessment.name,
            m.score,
            m.assessment.max_marks,
            m.percentage,
            m.remarks or ''
        ])
        
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment;filename=faculty_marks_{date.today()}.csv"}
    )
