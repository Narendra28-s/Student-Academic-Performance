from datetime import datetime, date, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

def get_utc_now():
    return datetime.now(timezone.utc)

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'faculty', 'parent'
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=get_utc_now)
    
    # 1-to-1 relationships
    faculty_profile = db.relationship('FacultyProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    parent_profile = db.relationship('ParentProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class AcademicClass(db.Model):
    __tablename__ = 'academic_classes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)       # e.g., "BE-CSE-3"
    section = db.Column(db.String(10), default='A')       # e.g., "A"
    department = db.Column(db.String(100), default='Computer Science')
    academic_year = db.Column(db.String(20), default='2025-2026')
    
    students = db.relationship('Student', backref='academic_class', lazy='dynamic', cascade='all, delete-orphan')
    faculty_assignments = db.relationship('FacultyClass', backref='academic_class', cascade='all, delete-orphan')
    assessments = db.relationship('Assessment', backref='academic_class', cascade='all, delete-orphan')
    attendance_records = db.relationship('Attendance', backref='academic_class', cascade='all, delete-orphan')
    
    @property
    def display_name(self):
        return f"{self.name} - Sec {self.section}"

    def __repr__(self):
        return f'<AcademicClass {self.display_name}>'


class Subject(db.Model):
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False) # e.g. "CS301"
    name = db.Column(db.String(100), nullable=False)            # e.g. "Data Structures"
    credits = db.Column(db.Integer, default=3)
    semester = db.Column(db.Integer, default=5)
    department = db.Column(db.String(100), default='Computer Science')
    
    assessments = db.relationship('Assessment', backref='subject', cascade='all, delete-orphan')
    faculty_assignments = db.relationship('FacultyClass', backref='subject', cascade='all, delete-orphan')
    feedback_records = db.relationship('FacultyFeedback', backref='subject', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Subject {self.code} - {self.name}>'


class FacultyProfile(db.Model):
    __tablename__ = 'faculty_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    employee_id = db.Column(db.String(30), unique=True, nullable=False)
    department = db.Column(db.String(100), default='Computer Science')
    designation = db.Column(db.String(50), default='Assistant Professor')
    qualification = db.Column(db.String(100), default='M.Tech, Ph.D')
    
    assignments = db.relationship('FacultyClass', backref='faculty', cascade='all, delete-orphan')
    feedback_given = db.relationship('FacultyFeedback', backref='faculty', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<FacultyProfile {self.employee_id}>'


class FacultyClass(db.Model):
    __tablename__ = 'faculty_classes'
    
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty_profiles.id', ondelete='CASCADE'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('academic_classes.id', ondelete='CASCADE'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('faculty_id', 'class_id', 'subject_id', name='uq_faculty_class_subject'),
    )


class ParentProfile(db.Model):
    __tablename__ = 'parent_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    occupation = db.Column(db.String(100), nullable=True)
    address = db.Column(db.Text, nullable=True)
    
    children_links = db.relationship('ParentStudent', backref='parent', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ParentProfile user_id={self.user_id}>'


class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(30), unique=True, nullable=False, index=True) # Roll/Reg No
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    gender = db.Column(db.String(10), default='Male')
    dob = db.Column(db.Date, nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('academic_classes.id', ondelete='CASCADE'), nullable=False)
    enrollment_date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(20), default='Active') # 'Active', 'Inactive', 'Suspended'
    study_hours_per_week = db.Column(db.Float, default=10.0)
    guardian_phone = db.Column(db.String(20), nullable=True)
    guardian_email = db.Column(db.String(120), nullable=True)
    
    # Relationships
    marks = db.relationship('Mark', backref='student', cascade='all, delete-orphan')
    attendance_records = db.relationship('Attendance', backref='student', cascade='all, delete-orphan')
    predictions = db.relationship('PredictionRecord', backref='student', cascade='all, delete-orphan', order_by='desc(PredictionRecord.generated_at)')
    feedbacks = db.relationship('FacultyFeedback', backref='student', cascade='all, delete-orphan', order_by='desc(FacultyFeedback.created_at)')
    parent_links = db.relationship('ParentStudent', backref='student', cascade='all, delete-orphan')

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
        
    def get_attendance_percentage(self):
        """Calculates attendance percentage (0 to 100)."""
        records = self.attendance_records
        if not records:
            return 100.0  # default when no records yet
        total = len(records)
        present = sum(1 for r in records if r.status in ['Present', 'Late'])
        return round((present / total) * 100, 1)

    def get_attendance_stats(self):
        records = self.attendance_records
        total = len(records)
        present = sum(1 for r in records if r.status == 'Present')
        late = sum(1 for r in records if r.status == 'Late')
        absent = sum(1 for r in records if r.status == 'Absent')
        excused = sum(1 for r in records if r.status == 'Excused')
        pct = round(((present + late) / total) * 100, 1) if total > 0 else 100.0
        return {
            'total': total,
            'present': present,
            'late': late,
            'absent': absent,
            'excused': excused,
            'percentage': pct
        }

    def get_average_marks(self):
        """Calculates average percentage score across all recorded assessments."""
        marks_list = self.marks
        if not marks_list:
            return 0.0
        valid_scores = []
        for m in marks_list:
            if m.assessment and m.assessment.max_marks > 0:
                pct = (m.score / m.assessment.max_marks) * 100.0
                valid_scores.append(pct)
        return round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else 0.0

    def get_subject_performance(self):
        """Returns subject-wise performance breakdown with average percentage."""
        perf = {}
        for m in self.marks:
            if not m.assessment or not m.assessment.subject:
                continue
            subj = m.assessment.subject
            if subj.name not in perf:
                perf[subj.name] = {
                    'subject_code': subj.code,
                    'subject_name': subj.name,
                    'scores': [],
                    'max_scores': [],
                    'marks': []
                }
            pct = (m.score / m.assessment.max_marks) * 100 if m.assessment.max_marks > 0 else 0
            perf[subj.name]['scores'].append(pct)
            perf[subj.name]['marks'].append(m)
            
        result = []
        for name, data in perf.items():
            avg_pct = round(sum(data['scores']) / len(data['scores']), 1) if data['scores'] else 0
            result.append({
                'subject_code': data['subject_code'],
                'subject_name': data['subject_name'],
                'average': avg_pct,
                'count': len(data['scores']),
                'status': 'Good' if avg_pct >= 65 else ('Warning' if avg_pct >= 50 else 'Critical')
            })
        return sorted(result, key=lambda x: x['average'])

    def get_latest_prediction(self):
        if self.predictions:
            return self.predictions[0]
        return None

    def __repr__(self):
        return f'<Student {self.student_id} - {self.full_name}>'


class ParentStudent(db.Model):
    __tablename__ = 'parent_students'
    
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('parent_profiles.id', ondelete='CASCADE'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    relationship = db.Column(db.String(50), default='Parent') # 'Father', 'Mother', 'Guardian'
    
    __table_args__ = (
        db.UniqueConstraint('parent_id', 'student_id', name='uq_parent_student'),
    )


class Assessment(db.Model):
    __tablename__ = 'assessments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)             # e.g., "Internal Test 1"
    assessment_type = db.Column(db.String(50), default='Internal Test') # 'Internal Test', 'Assignment', 'Quiz', 'Midterm'
    max_marks = db.Column(db.Float, default=100.0, nullable=False)
    weightage = db.Column(db.Float, default=20.0)                 # Percentage weight
    class_id = db.Column(db.Integer, db.ForeignKey('academic_classes.id', ondelete='CASCADE'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, default=date.today)
    
    marks = db.relationship('Mark', backref='assessment', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Assessment {self.name} - {self.subject.name if self.subject else ""}>'


class Mark(db.Model):
    __tablename__ = 'marks'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    remarks = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=get_utc_now, onupdate=get_utc_now)
    
    recorder = db.relationship('User', foreign_keys=[recorded_by])

    __table_args__ = (
        db.UniqueConstraint('student_id', 'assessment_id', name='uq_student_assessment_mark'),
    )

    @property
    def percentage(self):
        if self.assessment and self.assessment.max_marks > 0:
            return round((self.score / self.assessment.max_marks) * 100, 1)
        return 0.0

    def __repr__(self):
        return f'<Mark Student:{self.student_id} Assess:{self.assessment_id} Score:{self.score}>'


class Attendance(db.Model):
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('academic_classes.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Present', nullable=False) # 'Present', 'Absent', 'Late', 'Excused'
    remarks = db.Column(db.String(255), nullable=True)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    recorder = db.relationship('User', foreign_keys=[recorded_by])

    __table_args__ = (
        db.UniqueConstraint('student_id', 'date', name='uq_student_date_attendance'),
    )

    def __repr__(self):
        return f'<Attendance Student:{self.student_id} Date:{self.date} Status:{self.status}>'


class FacultyFeedback(db.Model):
    __tablename__ = 'faculty_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty_profiles.id', ondelete='CASCADE'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='SET NULL'), nullable=True)
    feedback_text = db.Column(db.Text, nullable=False)
    recommendation = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=get_utc_now)

    def __repr__(self):
        return f'<FacultyFeedback ID:{self.id} Student:{self.student_id}>'


class PredictionRecord(db.Model):
    __tablename__ = 'prediction_records'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    risk_level = db.Column(db.String(20), nullable=False)        # 'Low', 'Medium', 'High'
    probability = db.Column(db.Float, default=0.0)               # Risk probability (0.0 to 1.0)
    predicted_category = db.Column(db.String(50), nullable=False)# 'Good Standing', 'Moderate Risk', 'Critical Academic Risk'
    factors_json = db.Column(db.Text, nullable=True)             # JSON string of contributing factors
    suggestion_text = db.Column(db.Text, nullable=True)          # Academic improvement guidance
    generated_at = db.Column(db.DateTime, default=get_utc_now)

    @property
    def badge_class(self):
        if self.risk_level == 'High':
            return 'danger'
        elif self.risk_level == 'Medium':
            return 'warning'
        return 'success'

    def __repr__(self):
        return f'<PredictionRecord Student:{self.student_id} Risk:{self.risk_level}>'
