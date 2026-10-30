import os
import sys
from datetime import datetime, date, timedelta
import random

# Add parent directory to path so models and config can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import (
    db, User, AcademicClass, Subject, FacultyProfile, FacultyClass,
    Student, ParentProfile, ParentStudent, Assessment, Mark,
    Attendance, FacultyFeedback, PredictionRecord
)
from services.prediction_service import evaluate_all_students
from ml.train_model import train_and_save_model

def seed_database():
    app = create_app()
    with app.app_context():
        print("="*65)
        print("SEEDING STUDENT ACADEMIC MONITORING & PREDICTION SYSTEM DATABASE")
        print("="*65)
        
        # Ensure database tables are created
        db.create_all()
        
        # Check if already seeded
        if User.query.filter_by(email='admin@eft.edu').first():
            print("Database already contains demo data! Checking for missing ML predictions...")
            evaluate_all_students()
            print("Database is ready.")
            return

        print("\n[1/7] Creating Academic Classes...")
        class_cse_a = AcademicClass(name="BE-CSE-3", section="A", department="Computer Science & Eng", academic_year="2025-2026")
        class_cse_b = AcademicClass(name="BE-CSE-3", section="B", department="Computer Science & Eng", academic_year="2025-2026")
        class_it_a = AcademicClass(name="BE-IT-2", section="A", department="Information Technology", academic_year="2025-2026")
        
        db.session.add_all([class_cse_a, class_cse_b, class_it_a])
        db.session.flush()

        print("[2/7] Creating Academic Subjects...")
        subjects_data = [
            ("CS301", "Data Structures & Algorithms", 4, 5, "Computer Science & Eng"),
            ("CS302", "Database Management Systems", 4, 5, "Computer Science & Eng"),
            ("CS303", "Computer Networks", 3, 5, "Computer Science & Eng"),
            ("CS304", "Operating Systems", 3, 5, "Computer Science & Eng"),
            ("CS305", "Software Engineering", 3, 5, "Computer Science & Eng"),
            ("IT201", "Object Oriented Programming", 4, 3, "Information Technology"),
        ]
        created_subjects = {}
        for code, name, cred, sem, dept in subjects_data:
            s = Subject(code=code, name=name, credits=cred, semester=sem, department=dept)
            db.session.add(s)
            created_subjects[code] = s
        db.session.flush()

        print("[3/7] Creating Demo Users (Admin, Faculty, Parents)...")
        # 1. Admin
        admin = User(email="admin@eft.edu", role="admin", full_name="System Administrator", phone="+1 555-0100")
        admin.set_password("Admin@123")
        db.session.add(admin)

        # 2. Faculty Members
        faculty1 = User(email="faculty@eft.edu", role="faculty", full_name="Dr. Rajesh Sharma", phone="+1 555-0101")
        faculty1.set_password("Faculty@123")
        db.session.add(faculty1)
        db.session.flush()

        fac_prof1 = FacultyProfile(
            user_id=faculty1.id,
            employee_id="FAC-CSE-001",
            department="Computer Science & Eng",
            designation="Associate Professor",
            qualification="Ph.D. in Computer Science"
        )
        db.session.add(fac_prof1)

        faculty2 = User(email="faculty2@eft.edu", role="faculty", full_name="Prof. Priya Mehta", phone="+1 555-0102")
        faculty2.set_password("Faculty@123")
        db.session.add(faculty2)
        db.session.flush()

        fac_prof2 = FacultyProfile(
            user_id=faculty2.id,
            employee_id="FAC-IT-002",
            department="Information Technology",
            designation="Assistant Professor",
            qualification="M.Tech (Software Eng)"
        )
        db.session.add(fac_prof2)
        db.session.flush()

        # Faculty Assignments
        # Dr. Rajesh Sharma teaches CS301 and CS302 in BE-CSE-3A and BE-CSE-3B
        assign1 = FacultyClass(faculty_id=fac_prof1.id, class_id=class_cse_a.id, subject_id=created_subjects["CS301"].id)
        assign2 = FacultyClass(faculty_id=fac_prof1.id, class_id=class_cse_a.id, subject_id=created_subjects["CS302"].id)
        assign3 = FacultyClass(faculty_id=fac_prof1.id, class_id=class_cse_b.id, subject_id=created_subjects["CS301"].id)
        
        # Prof. Priya Mehta teaches CS303 and CS305 in BE-CSE-3A, and IT201 in BE-IT-2A
        assign4 = FacultyClass(faculty_id=fac_prof2.id, class_id=class_cse_a.id, subject_id=created_subjects["CS303"].id)
        assign5 = FacultyClass(faculty_id=fac_prof2.id, class_id=class_cse_a.id, subject_id=created_subjects["CS305"].id)
        assign6 = FacultyClass(faculty_id=fac_prof2.id, class_id=class_it_a.id, subject_id=created_subjects["IT201"].id)
        
        db.session.add_all([assign1, assign2, assign3, assign4, assign5, assign6])

        # 3. Parents
        # Parent 1: Mr. Robert Davis (Parent of John Davis)
        parent1 = User(email="parent@eft.edu", role="parent", full_name="Mr. Robert Davis", phone="+1 555-0103")
        parent1.set_password("Parent@123")
        db.session.add(parent1)
        db.session.flush()
        parent_prof1 = ParentProfile(user_id=parent1.id, occupation="Senior System Architect", address="42 Park Avenue, Metro City")
        db.session.add(parent_prof1)

        # Parent 2: Mrs. Sunita Sharma (Parent of 2 students: Priya Sharma & Rahul Sharma)
        parent2 = User(email="parent2@eft.edu", role="parent", full_name="Mrs. Sunita Sharma", phone="+1 555-0104")
        parent2.set_password("Parent@123")
        db.session.add(parent2)
        db.session.flush()
        parent_prof2 = ParentProfile(user_id=parent2.id, occupation="Management Consultant", address="15 Highland Crest, Metro City")
        db.session.add(parent_prof2)
        db.session.flush()

        print("[4/7] Creating Student Roster with Diverse Profiles...")
        # We will create 24 students across the 3 classes:
        # Some high performers, some average performers, and clearly defined at-risk students
        students_info = [
            # High Performers
            ("STU2025001", "John", "Davis", "john.davis@eft.edu", class_cse_a.id, "Male", 18.0, "high"),
            ("STU2025002", "Priya", "Sharma", "priya.sharma@eft.edu", class_cse_a.id, "Female", 20.0, "high"),
            ("STU2025004", "Aarav", "Patel", "aarav.patel@eft.edu", class_cse_a.id, "Male", 16.0, "high"),
            ("STU2025005", "Ananya", "Iyer", "ananya.iyer@eft.edu", class_cse_a.id, "Female", 17.5, "high"),
            
            # Average Performers
            ("STU2025003", "Rahul", "Sharma", "rahul.sharma@eft.edu", class_cse_a.id, "Male", 10.0, "med"),
            ("STU2025006", "Rohan", "Verma", "rohan.verma@eft.edu", class_cse_a.id, "Male", 11.0, "med"),
            ("STU2025007", "Neha", "Gupta", "neha.gupta@eft.edu", class_cse_a.id, "Female", 12.0, "med"),
            ("STU2025011", "Karthik", "Raman", "karthik.raman@eft.edu", class_cse_a.id, "Male", 9.5, "med"),
            ("STU2025012", "Divya", "Menon", "divya.menon@eft.edu", class_cse_a.id, "Female", 13.0, "high"),
            ("STU2025013", "Siddharth", "Joshi", "siddharth.joshi@eft.edu", class_cse_a.id, "Male", 8.0, "med"),
            
            # At-Risk Students (High Risk)
            ("STU2025008", "Kevin", "Miller", "kevin.miller@eft.edu", class_cse_a.id, "Male", 4.0, "critical"),
            ("STU2025009", "Vikram", "Singh", "vikram.singh@eft.edu", class_cse_a.id, "Male", 5.0, "critical"),
            ("STU2025010", "Sneha", "Reddy", "sneha.reddy@eft.edu", class_cse_a.id, "Female", 6.0, "critical"),
            
            # CSE-3B Students
            ("STU2025014", "Manish", "Tiwari", "manish.tiwari@eft.edu", class_cse_b.id, "Male", 14.0, "high"),
            ("STU2025015", "Pooja", "Nair", "pooja.nair@eft.edu", class_cse_b.id, "Female", 11.0, "med"),
            ("STU2025016", "Amit", "Kumar", "amit.kumar@eft.edu", class_cse_b.id, "Male", 5.5, "critical"),
            ("STU2025017", "Ritu", "Bansal", "ritu.bansal@eft.edu", class_cse_b.id, "Female", 15.0, "high"),
            ("STU2025018", "Varun", "Chopra", "varun.chopra@eft.edu", class_cse_b.id, "Male", 9.0, "med"),
            
            # IT-2A Students
            ("STU2025019", "Arjun", "Kapoor", "arjun.kapoor@eft.edu", class_it_a.id, "Male", 12.0, "med"),
            ("STU2025020", "Shreya", "Ghosh", "shreya.ghosh@eft.edu", class_it_a.id, "Female", 18.0, "high"),
            ("STU2025021", "Tanmay", "Bhat", "tanmay.bhat@eft.edu", class_it_a.id, "Male", 4.5, "critical"),
            ("STU2025022", "Kavya", "Madhavan", "kavya.madhavan@eft.edu", class_it_a.id, "Female", 14.0, "high"),
        ]

        created_students = {}
        for sid, fname, lname, em, cid, gen, hours, ptype in students_info:
            stu = Student(
                student_id=sid,
                first_name=fname,
                last_name=lname,
                email=em,
                class_id=cid,
                gender=gen,
                study_hours_per_week=hours,
                guardian_phone="+1 555-9000",
                guardian_email=f"parent.{lname.lower()}@gmail.com"
            )
            stu._profile_type = ptype # transient tag
            db.session.add(stu)
            created_students[sid] = stu

        db.session.flush()

        # Link Parents to Students:
        # Parent 1 (Robert Davis) -> John Davis (STU2025001)
        link1 = ParentStudent(parent_id=parent_prof1.id, student_id=created_students["STU2025001"].id, relationship="Father")
        # Parent 2 (Sunita Sharma) -> Priya Sharma (STU2025002) & Rahul Sharma (STU2025003)
        link2 = ParentStudent(parent_id=parent_prof2.id, student_id=created_students["STU2025002"].id, relationship="Mother")
        link3 = ParentStudent(parent_id=parent_prof2.id, student_id=created_students["STU2025003"].id, relationship="Mother")
        db.session.add_all([link1, link2, link3])

        print("[5/7] Creating Assessments and Recording Realistic Student Marks...")
        # Assessments for CSE-3A
        today = date.today()
        assessments_data = [
            ("Internal Test 1", "Internal Test", 50.0, 20.0, class_cse_a.id, created_subjects["CS301"].id, today - timedelta(days=45)),
            ("Internal Test 2", "Internal Test", 50.0, 20.0, class_cse_a.id, created_subjects["CS301"].id, today - timedelta(days=15)),
            ("Assignment 1", "Assignment", 25.0, 10.0, class_cse_a.id, created_subjects["CS301"].id, today - timedelta(days=30)),
            
            ("Internal Test 1", "Internal Test", 50.0, 20.0, class_cse_a.id, created_subjects["CS302"].id, today - timedelta(days=40)),
            ("Internal Test 2", "Internal Test", 50.0, 20.0, class_cse_a.id, created_subjects["CS302"].id, today - timedelta(days=12)),
            ("Assignment 1", "Assignment", 25.0, 10.0, class_cse_a.id, created_subjects["CS302"].id, today - timedelta(days=25)),

            ("Internal Test 1", "Internal Test", 50.0, 20.0, class_cse_a.id, created_subjects["CS303"].id, today - timedelta(days=35)),
            ("Assignment 1", "Assignment", 25.0, 10.0, class_cse_a.id, created_subjects["CS303"].id, today - timedelta(days=20)),

            ("Internal Test 1", "Internal Test", 50.0, 20.0, class_cse_a.id, created_subjects["CS305"].id, today - timedelta(days=32)),
            ("Mini Project 1", "Project", 50.0, 20.0, class_cse_a.id, created_subjects["CS305"].id, today - timedelta(days=10)),

            # Assessments for CSE-3B
            ("Internal Test 1", "Internal Test", 50.0, 20.0, class_cse_b.id, created_subjects["CS301"].id, today - timedelta(days=42)),
            ("Internal Test 2", "Internal Test", 50.0, 20.0, class_cse_b.id, created_subjects["CS301"].id, today - timedelta(days=14)),

            # Assessments for IT-2A
            ("Internal Test 1", "Internal Test", 50.0, 20.0, class_it_a.id, created_subjects["IT201"].id, today - timedelta(days=38)),
            ("Lab Quiz 1", "Quiz", 20.0, 10.0, class_it_a.id, created_subjects["IT201"].id, today - timedelta(days=18)),
        ]

        created_assessments = []
        for name, atype, mmax, weight, cid, subjid, adate in assessments_data:
            a = Assessment(
                name=name,
                assessment_type=atype,
                max_marks=mmax,
                weightage=weight,
                class_id=cid,
                subject_id=subjid,
                date=adate
            )
            db.session.add(a)
            created_assessments.append(a)

        db.session.flush()

        # Generate realistic marks for each student based on their profile type
        random.seed(42)
        for a in created_assessments:
            # find students in that assessment's class
            class_students = [s for s in created_students.values() if s.class_id == a.class_id]
            for stu in class_students:
                ptype = getattr(stu, '_profile_type', 'med')
                if ptype == 'high':
                    # 78% - 98%
                    pct = random.uniform(0.78, 0.98)
                    remarks = "Excellent understanding and clear solution methodology."
                elif ptype == 'med':
                    # 52% - 76%
                    pct = random.uniform(0.52, 0.76)
                    remarks = "Fair performance. Good effort shown; revise complex algorithms."
                else: # critical
                    # 22% - 46%
                    pct = random.uniform(0.22, 0.46)
                    remarks = "Needs immediate improvement. Concept gaps identified in foundational topics."
                    
                score = round(pct * a.max_marks, 1)
                mark = Mark(
                    student_id=stu.id,
                    assessment_id=a.id,
                    score=min(score, a.max_marks),
                    recorded_by=faculty1.id,
                    remarks=remarks
                )
                db.session.add(mark)

        print("[6/7] Generating Historical Daily Attendance Records (Past 30 Days)...")
        # Attendance dates: past 30 days excluding weekends
        att_dates = []
        curr = today - timedelta(days=40)
        while curr <= today:
            if curr.weekday() < 5: # Monday - Friday
                att_dates.append(curr)
            curr += timedelta(days=1)
        att_dates = att_dates[-25:] # last 25 instructional days

        for s in created_students.values():
            ptype = getattr(s, '_profile_type', 'med')
            # attendance probability
            if ptype == 'high':
                prob_present = 0.94
                prob_late = 0.04
            elif ptype == 'med':
                prob_present = 0.80
                prob_late = 0.08
            else: # critical
                prob_present = 0.52
                prob_late = 0.08
                
            for dt in att_dates:
                rand_val = random.random()
                if rand_val < prob_present:
                    st = 'Present'
                    rem = ''
                elif rand_val < (prob_present + prob_late):
                    st = 'Late'
                    rem = 'Arrived 10 mins late'
                else:
                    st = 'Absent'
                    rem = 'Unexcused Absence'
                    
                att = Attendance(
                    student_id=s.id,
                    class_id=s.class_id,
                    date=dt,
                    status=st,
                    remarks=rem,
                    recorded_by=faculty1.id
                )
                db.session.add(att)

        print("[7/7] Adding Faculty Feedback and Computing ML Predictions...")
        # Add feedback from Dr. Rajesh Sharma
        fb1 = FacultyFeedback(
            student_id=created_students["STU2025001"].id, # John Davis
            faculty_id=fac_prof1.id,
            subject_id=created_subjects["CS301"].id,
            feedback_text="John exhibits exceptional algorithmic thinking and active class participation.",
            recommendation="Recommend participating in ACM-ICPC competitive programming events."
        )
        fb2 = FacultyFeedback(
            student_id=created_students["STU2025002"].id, # Priya Sharma
            faculty_id=fac_prof1.id,
            subject_id=created_subjects["CS302"].id,
            feedback_text="Consistently achieves top scores in relational queries and normalization.",
            recommendation="Encouraged to pursue an advanced DBMS research project."
        )
        fb3 = FacultyFeedback(
            student_id=created_students["STU2025003"].id, # Rahul Sharma
            faculty_id=fac_prof1.id,
            subject_id=created_subjects["CS301"].id,
            feedback_text="Rahul grasps theoretical concepts well but needs more hands-on coding practice.",
            recommendation="Practice 3-4 tree traversal and dynamic programming questions weekly."
        )
        fb4 = FacultyFeedback(
            student_id=created_students["STU2025008"].id, # Kevin Miller
            faculty_id=fac_prof1.id,
            subject_id=created_subjects["CS301"].id,
            feedback_text="Kevin has missed key lectures and struggled with basic pointer arithmetic and graph algorithms.",
            recommendation="Mandatory remedial tutoring sessions on Tuesdays. Attendance must improve immediately."
        )
        db.session.add_all([fb1, fb2, fb3, fb4])
        
        db.session.commit()
        print("Database commit successful.")

        # Train ML model if not already trained
        train_and_save_model()

        # Evaluate and create prediction records for all students
        updated_count = evaluate_all_students()
        print(f"Generated Machine Learning Risk Predictions for {updated_count} students.")

        print("\n" + "="*65)
        print("DATABASE INITIALIZATION COMPLETE!")
        print("Demo Accounts Created:")
        print("  Admin   : admin@eft.edu   / Admin@123")
        print("  Faculty : faculty@eft.edu / Faculty@123 (Dr. Rajesh Sharma)")
        print("  Faculty : faculty2@eft.edu / Faculty@123 (Prof. Priya Mehta)")
        print("  Parent  : parent@eft.edu  / Parent@123 (Child: John Davis)")
        print("  Parent  : parent2@eft.edu / Parent@123 (Children: Priya Sharma & Rahul Sharma)")
        print("="*65 + "\n")

if __name__ == '__main__':
    seed_database()
