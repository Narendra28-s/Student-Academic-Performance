import io
import csv
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, jsonify
from models import (
    db, User, Student, AcademicClass, FacultyProfile, FacultyClass,
    Subject, Assessment, Mark, Attendance, ParentProfile, ParentStudent,
    PredictionRecord, FacultyFeedback
)
from auth import login_required, role_required, get_current_user
from services.analytics import get_admin_dashboard_metrics
from services.prediction_service import update_or_create_prediction, evaluate_all_students, get_model_performance_metrics
from ml.train_model import train_and_save_model

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@login_required
@role_required('admin')
def enforce_admin_access():
    pass

# ==========================================
# 1. ADMIN DASHBOARD
# ==========================================
@admin_bp.route('/dashboard')
def dashboard():
    metrics = get_admin_dashboard_metrics()
    model_metrics = get_model_performance_metrics()
    return render_template('admin/dashboard.html', metrics=metrics, model_metrics=model_metrics)

# ==========================================
# 2. STUDENT MANAGEMENT (CRUD + Search/Filter)
# ==========================================
@admin_bp.route('/students')
def students():
    search_query = request.args.get('q', '').strip()
    class_filter = request.args.get('class_id', '')
    status_filter = request.args.get('status', '')
    
    query = Student.query
    if search_query:
        query = query.filter(
            (Student.first_name.ilike(f'%{search_query}%')) |
            (Student.last_name.ilike(f'%{search_query}%')) |
            (Student.student_id.ilike(f'%{search_query}%')) |
            (Student.email.ilike(f'%{search_query}%'))
        )
    if class_filter:
        query = query.filter_by(class_id=int(class_filter))
    if status_filter:
        query = query.filter_by(status=status_filter)
        
    students_list = query.order_by(Student.student_id).all()
    classes = AcademicClass.query.order_by(AcademicClass.name).all()
    
    return render_template(
        'admin/students.html',
        students=students_list,
        classes=classes,
        search_query=search_query,
        class_filter=class_filter,
        status_filter=status_filter
    )

@admin_bp.route('/students/add', methods=['GET', 'POST'])
def add_student():
    classes = AcademicClass.query.order_by(AcademicClass.name).all()
    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        class_id = request.form.get('class_id')
        gender = request.form.get('gender', 'Male')
        study_hours = request.form.get('study_hours', 10.0)
        guardian_phone = request.form.get('guardian_phone', '').strip()
        guardian_email = request.form.get('guardian_email', '').strip()
        
        # Validation
        if not student_id or not first_name or not last_name or not email or not class_id:
            flash('Please fill in all required fields.', 'danger')
            return render_template('admin/student_form.html', classes=classes, action='Add')
            
        if Student.query.filter_by(student_id=student_id).first():
            flash(f'Student ID "{student_id}" is already registered. Please use a unique ID.', 'danger')
            return render_template('admin/student_form.html', classes=classes, action='Add')
            
        if Student.query.filter_by(email=email).first():
            flash(f'Email "{email}" is already used by another student.', 'danger')
            return render_template('admin/student_form.html', classes=classes, action='Add')
            
        try:
            student = Student(
                student_id=student_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                class_id=int(class_id),
                gender=gender,
                study_hours_per_week=float(study_hours) if study_hours else 10.0,
                guardian_phone=guardian_phone,
                guardian_email=guardian_email
            )
            db.session.add(student)
            db.session.commit()
            
            # Generate initial prediction
            update_or_create_prediction(student)
            
            flash(f'Student "{student.full_name}" (ID: {student.student_id}) successfully added!', 'success')
            return redirect(url_for('admin.students'))
        except Exception as e:
            db.session.rollback()
            flash(f'Database error while creating student: {str(e)}', 'danger')
            
    return render_template('admin/student_form.html', classes=classes, action='Add', student=None)

@admin_bp.route('/students/edit/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    student = db.session.get(Student, id)
    if not student:
        flash('Student record not found.', 'danger')
        return redirect(url_for('admin.students'))
        
    classes = AcademicClass.query.order_by(AcademicClass.name).all()
    
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        class_id = request.form.get('class_id')
        gender = request.form.get('gender')
        status = request.form.get('status', 'Active')
        study_hours = request.form.get('study_hours')
        guardian_phone = request.form.get('guardian_phone', '').strip()
        guardian_email = request.form.get('guardian_email', '').strip()
        
        # Unique email check excluding self
        existing = Student.query.filter(Student.email == email, Student.id != id).first()
        if existing:
            flash(f'Email "{email}" is already taken by another student.', 'danger')
            return render_template('admin/student_form.html', classes=classes, action='Edit', student=student)
            
        try:
            student.first_name = first_name
            student.last_name = last_name
            student.email = email
            student.class_id = int(class_id)
            student.gender = gender
            student.status = status
            student.study_hours_per_week = float(study_hours) if study_hours else 10.0
            student.guardian_phone = guardian_phone
            student.guardian_email = guardian_email
            
            db.session.commit()
            update_or_create_prediction(student)
            
            flash(f'Student "{student.full_name}" updated successfully.', 'success')
            return redirect(url_for('admin.students'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating student: {str(e)}', 'danger')
            
    return render_template('admin/student_form.html', classes=classes, action='Edit', student=student)

@admin_bp.route('/students/delete/<int:id>', methods=['POST'])
def delete_student(id):
    student = db.session.get(Student, id)
    if not student:
        flash('Student record not found.', 'danger')
        return redirect(url_for('admin.students'))
        
    name = student.full_name
    student_id = student.student_id
    try:
        db.session.delete(student)
        db.session.commit()
        flash(f'Student "{name}" ({student_id}) and associated records deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Cannot delete student: {str(e)}', 'danger')
        
    return redirect(url_for('admin.students'))

@admin_bp.route('/students/view/<int:id>')
def view_student(id):
    student = db.session.get(Student, id)
    if not student:
        flash('Student record not found.', 'danger')
        return redirect(url_for('admin.students'))
        
    # Re-evaluate prediction to keep it fresh
    pred, pred_details = update_or_create_prediction(student)
    
    # Marks and attendance
    marks = Mark.query.filter_by(student_id=student.id).join(Assessment).order_by(Assessment.date.desc()).all()
    attendance = Attendance.query.filter_by(student_id=student.id).order_by(Attendance.date.desc()).all()
    feedbacks = FacultyFeedback.query.filter_by(student_id=student.id).order_by(FacultyFeedback.created_at.desc()).all()
    
    return render_template(
        'admin/student_detail.html',
        student=student,
        marks=marks,
        attendance=attendance,
        feedbacks=feedbacks,
        prediction=pred,
        pred_details=pred_details
    )

# ==========================================
# 3. FACULTY MANAGEMENT
# ==========================================
@admin_bp.route('/faculty')
def faculty_list():
    faculties = FacultyProfile.query.all()
    classes = AcademicClass.query.all()
    subjects = Subject.query.all()
    return render_template('admin/faculty.html', faculties=faculties, classes=classes, subjects=subjects)

@admin_bp.route('/faculty/add', methods=['GET', 'POST'])
def add_faculty():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', 'Faculty@123')
        employee_id = request.form.get('employee_id', '').strip()
        department = request.form.get('department', 'Computer Science').strip()
        designation = request.form.get('designation', 'Assistant Professor').strip()
        qualification = request.form.get('qualification', 'M.Tech').strip()
        phone = request.form.get('phone', '').strip()
        
        if not full_name or not email or not employee_id:
            flash('Full name, email, and Employee ID are required.', 'danger')
            return render_template('admin/faculty_form.html', action='Add', faculty=None)
            
        if User.query.filter_by(email=email).first():
            flash(f'User with email "{email}" already exists.', 'danger')
            return render_template('admin/faculty_form.html', action='Add', faculty=None)
            
        if FacultyProfile.query.filter_by(employee_id=employee_id).first():
            flash(f'Employee ID "{employee_id}" is already assigned.', 'danger')
            return render_template('admin/faculty_form.html', action='Add', faculty=None)
            
        try:
            user = User(
                email=email,
                role='faculty',
                full_name=full_name,
                phone=phone
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush() # obtain user.id
            
            profile = FacultyProfile(
                user_id=user.id,
                employee_id=employee_id,
                department=department,
                designation=designation,
                qualification=qualification
            )
            db.session.add(profile)
            db.session.commit()
            
            flash(f'Faculty account created for "{full_name}" ({employee_id}).', 'success')
            return redirect(url_for('admin.faculty_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating faculty: {str(e)}', 'danger')
            
    return render_template('admin/faculty_form.html', action='Add', faculty=None)

@admin_bp.route('/faculty/toggle-status/<int:id>', methods=['POST'])
def toggle_faculty_status(id):
    profile = db.session.get(FacultyProfile, id)
    if profile and profile.user:
        profile.user.is_active = not profile.user.is_active
        db.session.commit()
        status_str = "activated" if profile.user.is_active else "deactivated"
        flash(f'Faculty "{profile.user.full_name}" account has been {status_str}.', 'info')
    return redirect(url_for('admin.faculty_list'))

@admin_bp.route('/faculty/assign', methods=['POST'])
def assign_faculty():
    faculty_id = request.form.get('faculty_id')
    class_id = request.form.get('class_id')
    subject_id = request.form.get('subject_id')
    
    if not faculty_id or not class_id or not subject_id:
        flash('Faculty, Class, and Subject must all be selected.', 'warning')
        return redirect(url_for('admin.faculty_list'))
        
    existing = FacultyClass.query.filter_by(
        faculty_id=int(faculty_id),
        class_id=int(class_id),
        subject_id=int(subject_id)
    ).first()
    
    if existing:
        flash('This faculty member is already assigned to this class and subject.', 'warning')
        return redirect(url_for('admin.faculty_list'))
        
    try:
        assignment = FacultyClass(
            faculty_id=int(faculty_id),
            class_id=int(class_id),
            subject_id=int(subject_id)
        )
        db.session.add(assignment)
        db.session.commit()
        flash('Class & Subject assigned to faculty successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Assignment failed: {str(e)}', 'danger')
        
    return redirect(url_for('admin.faculty_list'))

@admin_bp.route('/faculty/unassign/<int:assignment_id>', methods=['POST'])
def unassign_faculty(assignment_id):
    assignment = db.session.get(FacultyClass, assignment_id)
    if assignment:
        db.session.delete(assignment)
        db.session.commit()
        flash('Teaching assignment removed.', 'info')
    return redirect(url_for('admin.faculty_list'))

# ==========================================
# 4. PARENT MANAGEMENT & STUDENT LINKING
# ==========================================
@admin_bp.route('/parents')
def parents_list():
    parents = ParentProfile.query.all()
    students = Student.query.order_by(Student.student_id).all()
    return render_template('admin/parents.html', parents=parents, students=students)

@admin_bp.route('/parents/add', methods=['GET', 'POST'])
def add_parent():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', 'Parent@123')
        phone = request.form.get('phone', '').strip()
        occupation = request.form.get('occupation', '').strip()
        address = request.form.get('address', '').strip()
        
        if not full_name or not email:
            flash('Parent name and email are required.', 'danger')
            return render_template('admin/parent_form.html', action='Add')
            
        if User.query.filter_by(email=email).first():
            flash(f'Account with email "{email}" already exists.', 'danger')
            return render_template('admin/parent_form.html', action='Add')
            
        try:
            user = User(
                email=email,
                role='parent',
                full_name=full_name,
                phone=phone
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            
            profile = ParentProfile(
                user_id=user.id,
                occupation=occupation,
                address=address
            )
            db.session.add(profile)
            db.session.commit()
            
            flash(f'Parent account for "{full_name}" registered successfully.', 'success')
            return redirect(url_for('admin.parents_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error registering parent: {str(e)}', 'danger')
            
    return render_template('admin/parent_form.html', action='Add')

@admin_bp.route('/parents/link', methods=['POST'])
def link_parent_student():
    parent_id = request.form.get('parent_id')
    student_id = request.form.get('student_id')
    relationship = request.form.get('relationship', 'Parent')
    
    if not parent_id or not student_id:
        flash('Both parent and student must be selected.', 'warning')
        return redirect(url_for('admin.parents_list'))
        
    existing = ParentStudent.query.filter_by(
        parent_id=int(parent_id),
        student_id=int(student_id)
    ).first()
    
    if existing:
        flash('This student is already linked to this parent account.', 'warning')
        return redirect(url_for('admin.parents_list'))
        
    try:
        link = ParentStudent(
            parent_id=int(parent_id),
            student_id=int(student_id),
            relationship=relationship
        )
        db.session.add(link)
        db.session.commit()
        flash('Student successfully linked to parent!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error linking student: {str(e)}', 'danger')
        
    return redirect(url_for('admin.parents_list'))

@admin_bp.route('/parents/unlink/<int:link_id>', methods=['POST'])
def unlink_parent_student(link_id):
    link = db.session.get(ParentStudent, link_id)
    if link:
        db.session.delete(link)
        db.session.commit()
        flash('Student unlinked from parent account.', 'info')
    return redirect(url_for('admin.parents_list'))

# ==========================================
# 5. CLASSES & SUBJECTS MANAGEMENT
# ==========================================
@admin_bp.route('/classes', methods=['GET', 'POST'])
def classes_list():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        section = request.form.get('section', 'A').strip().upper()
        department = request.form.get('department', 'Computer Science').strip()
        academic_year = request.form.get('academic_year', '2025-2026').strip()
        
        if not name:
            flash('Class name cannot be empty.', 'danger')
        else:
            try:
                new_class = AcademicClass(
                    name=name,
                    section=section,
                    department=department,
                    academic_year=academic_year
                )
                db.session.add(new_class)
                db.session.commit()
                flash(f'Class "{new_class.display_name}" created successfully.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Failed to create class: {str(e)}', 'danger')
                
    classes = AcademicClass.query.order_by(AcademicClass.name, AcademicClass.section).all()
    return render_template('admin/classes.html', classes=classes)

@admin_bp.route('/subjects', methods=['GET', 'POST'])
def subjects_list():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()
        credits = request.form.get('credits', 3)
        semester = request.form.get('semester', 5)
        department = request.form.get('department', 'Computer Science').strip()
        
        if not code or not name:
            flash('Subject code and name are required.', 'danger')
        elif Subject.query.filter_by(code=code).first():
            flash(f'Subject with code "{code}" already exists.', 'danger')
        else:
            try:
                subj = Subject(
                    code=code,
                    name=name,
                    credits=int(credits),
                    semester=int(semester),
                    department=department
                )
                db.session.add(subj)
                db.session.commit()
                flash(f'Subject "{code} - {name}" added successfully.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Failed to add subject: {str(e)}', 'danger')
                
    subjects = Subject.query.order_by(Subject.code).all()
    return render_template('admin/subjects.html', subjects=subjects)

# ==========================================
# 6. MARKS & ATTENDANCE VIEWS
# ==========================================
@admin_bp.route('/marks')
def view_marks():
    class_id = request.args.get('class_id', '')
    subject_id = request.args.get('subject_id', '')
    
    query = Mark.query.join(Assessment)
    if class_id:
        query = query.filter(Assessment.class_id == int(class_id))
    if subject_id:
        query = query.filter(Assessment.subject_id == int(subject_id))
        
    marks_list = query.order_by(Assessment.date.desc()).all()
    classes = AcademicClass.query.all()
    subjects = Subject.query.all()
    
    return render_template(
        'admin/marks.html',
        marks=marks_list,
        classes=classes,
        subjects=subjects,
        selected_class=class_id,
        selected_subject=subject_id
    )

@admin_bp.route('/attendance')
def view_attendance():
    class_id = request.args.get('class_id', '')
    date_filter = request.args.get('date', '')
    status_filter = request.args.get('status', '')
    
    query = Attendance.query
    if class_id:
        query = query.filter_by(class_id=int(class_id))
    if date_filter:
        try:
            d = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter_by(date=d)
        except ValueError:
            pass
    if status_filter:
        query = query.filter_by(status=status_filter)
        
    attendance_records = query.order_by(Attendance.date.desc()).limit(200).all()
    classes = AcademicClass.query.all()
    
    return render_template(
        'admin/attendance.html',
        records=attendance_records,
        classes=classes,
        selected_class=class_id,
        selected_date=date_filter,
        selected_status=status_filter
    )

# ==========================================
# 7. MACHINE LEARNING PREDICTIONS MANAGEMENT
# ==========================================
@admin_bp.route('/predictions')
def predictions():
    risk_filter = request.args.get('risk', '')
    query = PredictionRecord.query.join(Student)
    if risk_filter:
        query = query.filter(PredictionRecord.risk_level == risk_filter)
        
    predictions_list = query.order_by(PredictionRecord.generated_at.desc()).all()
    metrics = get_model_performance_metrics()
    
    return render_template(
        'admin/predictions.html',
        predictions=predictions_list,
        model_metrics=metrics,
        selected_risk=risk_filter
    )

@admin_bp.route('/predictions/re-evaluate', methods=['POST'])
def trigger_reevaluation():
    count = evaluate_all_students()
    flash(f'Successfully re-evaluated academic risk predictions for all {count} students!', 'success')
    return redirect(url_for('admin.predictions'))

@admin_bp.route('/predictions/retrain-model', methods=['POST'])
def trigger_retrain():
    try:
        model_path, metrics = train_and_save_model()
        evaluate_all_students()
        flash(f"ML Model retrained successfully! Test Accuracy: {metrics['accuracy']}%, F1 Score: {metrics['f1_score']}%. All student risks updated.", 'success')
    except Exception as e:
        flash(f"Model retraining failed: {str(e)}", 'danger')
    return redirect(url_for('admin.predictions'))

# ==========================================
# 8. CSV EXPORTS
# ==========================================
@admin_bp.route('/export/students')
def export_students_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Student ID', 'First Name', 'Last Name', 'Email', 'Class',
        'Gender', 'Status', 'Study Hours/Week', 'Avg Marks %', 'Attendance %', 'Risk Level'
    ])
    
    for s in Student.query.all():
        pred = s.get_latest_prediction()
        risk = pred.risk_level if pred else 'N/A'
        writer.writerow([
            s.student_id,
            s.first_name,
            s.last_name,
            s.email,
            s.academic_class.display_name,
            s.gender,
            s.status,
            s.study_hours_per_week,
            s.get_average_marks(),
            s.get_attendance_percentage(),
            risk
        ])
        
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment;filename=students_report_{date.today()}.csv"}
    )

@admin_bp.route('/export/marks')
def export_marks_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Student ID', 'Student Name', 'Class', 'Subject Code',
        'Subject Name', 'Assessment', 'Assessment Type', 'Score', 'Max Marks', 'Percentage %', 'Remarks'
    ])
    
    marks = Mark.query.join(Assessment).all()
    for m in marks:
        writer.writerow([
            m.student.student_id,
            m.student.full_name,
            m.assessment.academic_class.display_name,
            m.assessment.subject.code,
            m.assessment.subject.name,
            m.assessment.name,
            m.assessment.assessment_type,
            m.score,
            m.assessment.max_marks,
            m.percentage,
            m.remarks or ''
        ])
        
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment;filename=academic_marks_report_{date.today()}.csv"}
    )

@admin_bp.route('/export/attendance')
def export_attendance_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Date', 'Student ID', 'Student Name', 'Class', 'Status', 'Remarks'
    ])
    
    records = Attendance.query.order_by(Attendance.date.desc()).all()
    for r in records:
        writer.writerow([
            r.date.strftime('%Y-%m-%d'),
            r.student.student_id,
            r.student.full_name,
            r.academic_class.display_name,
            r.status,
            r.remarks or ''
        ])
        
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment;filename=attendance_report_{date.today()}.csv"}
    )

@admin_bp.route('/export/predictions')
def export_predictions_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Student ID', 'Student Name', 'Class', 'Risk Level',
        'Risk Category', 'Risk Probability', 'Attendance %', 'Average Marks %', 'Suggestions', 'Evaluated At'
    ])
    
    for s in Student.query.all():
        pred = s.get_latest_prediction()
        if pred:
            writer.writerow([
                s.student_id,
                s.full_name,
                s.academic_class.display_name,
                pred.risk_level,
                pred.predicted_category,
                pred.probability,
                s.get_attendance_percentage(),
                s.get_average_marks(),
                pred.suggestion_text.replace('\n', ' | ') if pred.suggestion_text else '',
                pred.generated_at.strftime('%Y-%m-%d %H:%M')
            ])
            
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment;filename=academic_risk_predictions_{date.today()}.csv"}
    )
