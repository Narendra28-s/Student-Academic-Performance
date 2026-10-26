# Student Academic Performance Monitoring and Prediction System

A full-stack, enterprise-grade academic monitoring and machine learning risk prediction web application developed for final year engineering/academic demonstration (EFT Project).

Built with **Python Flask**, **SQLite (Flask-SQLAlchemy)**, **Bootstrap 5**, **Chart.js**, and **scikit-learn**.

---

## 🌟 Key System Features

The application provides three separate, secure, role-based dashboards:

### 1. 🛡️ Admin Dashboard (Full System Management)
- **Live Institutional Metrics**: Total students, total faculty, total classes, institutional average score, students at risk count, and overall attendance rate.
- **Dynamic Chart.js Visualizations**:
  - Class-wise performance comparison
  - Subject-wise average marks
  - Attendance distribution tiers (Excellent, Good, Warning, Critical)
  - Pass/Fail distribution (based on >=50% passing threshold)
  - At-Risk distribution by class (Stacked Bar)
- **Student CRUD Management**: Add, view, edit, search (by name, roll ID, email), filter (by class, status), and delete student records with confirmation modals.
- **Faculty Management**: Register faculty profiles, toggle account active status, and assign faculty to classes & subjects.
- **Parent Management**: Register parent accounts and link parents to one or multiple students.
- **Academic Setup**: Class and subject creation.
- **Institutional Records**: View and filter marks and attendance logs.
- **AI Risk Matrix**: View system-wide machine learning predictions, trigger re-evaluation, or retrain the Random Forest model.
- **CSV Data Export**: One-click downloadable CSV reports for Students, Marks, Attendance, and Risk Predictions.

### 2. 👨‍🏫 Faculty Dashboard (Academic Operations)
- **Classroom Scoping**: Access restricted strictly to assigned classes and subjects.
- **Batch Marks Entry**: Enter and update internal test, assignment, quiz, and midterm marks with score validation against configured maximum marks.
- **Daily Attendance Recording**: Date-based daily attendance roster with Present, Absent, and Late status, including duplicate entry prevention for the same date.
- **Student Performance Analysis**: View detailed student profiles, assessment progression, and faculty feedback history.
- **Performance Decline Alerts**: Automatically detects and highlights students whose scores dropped by >8% between recent assessments.
- **Actionable Faculty Feedback**: Submit academic observations and improvement recommendations directly visible to students and parents.
- **CSV Export**: Export subject-wise marks for assigned classes.

### 3. 👨‍👩‍👧 Parent Dashboard (Child Performance Tracking)
- **Child-Specific Access**: Isolated data visibility restricted only to linked children.
- **Multi-Child Switcher**: Effortlessly toggle between siblings if multiple children are associated with the account.
- **Summary Cards**: Child's overall average score, attendance percentage, count of subjects requiring attention (<60%), and academic standing.
- **Interactive Progress Charts**:
  - Longitudinal performance progress trend line chart
  - Subject-wise comparison bar chart
- **Attendance Breakdown**: Total days, present days, absent days, and late arrivals with daily log.
- **Instructor Feedback Cards**: View personalized teacher observations and recommendations.
- **Plain-English Academic Standing**: Plain-language risk guidance and home action steps without technical jargon.

---

## 🤖 Machine Learning Academic Risk Engine

- **Model**: `RandomForestClassifier` with `StandardScaler` inside a scikit-learn pipeline.
- **Reproducible Pipeline**: Documented in `ml/train_model.py`.
- **Features Used**:
  1. `attendance_pct` (Classroom attendance percentage)
  2. `internal_test_avg` (Average percentage on internal assessments)
  3. `assignment_avg` (Average percentage on homework & projects)
  4. `quiz_avg` (Average percentage on quizzes)
  5. `study_hours` (Weekly reported independent self-study hours)
  6. `failed_assessments_count` (Number of assessments scored <50%)
- **Target Risk Categories**:
  - `Low Risk` (Satisfactory Standing)
  - `Medium Risk` (Academic Attention Recommended)
  - `High Risk` (Critical Academic Intervention Needed)
- **Evaluation**: Evaluated on held-out stratified test data with classification reports, confusion matrices, and feature importances stored in `ml/saved_models/model_metrics.json`.
- **Fault-Tolerant Fallback**: Built-in rule-based heuristic engine activates automatically if the ML model artifact is missing or during data initialization.

---

## 🔑 Demonstration Accounts

The database comes pre-seeded with realistic academic data. You can log in using any of the accounts below:

| Role | Email | Password | Details / Assigned Scope |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@eft.edu` | `Admin@123` | System Administrator (Full System Access) |
| **Faculty 1** | `faculty@eft.edu` | `Faculty@123` | Dr. Rajesh Sharma (Dept of CSE: Data Structures, DBMS) |
| **Faculty 2** | `faculty2@eft.edu` | `Faculty@123` | Prof. Priya Mehta (Dept of IT: Networks, Software Eng) |
| **Parent 1** | `parent@eft.edu` | `Parent@123` | Mr. Robert Davis (Child: John Davis) |
| **Parent 2** | `parent2@eft.edu` | `Parent@123` | Mrs. Sunita Sharma (**Multi-Child**: Priya Sharma & Rahul Sharma) |

> **Note**: One-click quick-fill buttons are provided on the login page for convenience during evaluation.

---

## 💻 Installation and Running on Windows

### Prerequisites
- Python 3.10+ (Python 3.13 tested and verified)
- Windows PowerShell or Command Prompt

### Step 1: Clone or Navigate to Project Directory
```powershell
cd "c:\Users\naren\OneDrive\Desktop\EFT Final project"
```

### Step 2: (Optional) Create and Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If PowerShell restricts script execution, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Initialize and Seed Demo Database
```powershell
python scripts/seed_data.py
```
This sets up classes, subjects, faculty profiles, 22 student records across 3 classes, 30 days of attendance, assessments, marks, faculty feedback, trains the Random Forest model, and generates initial risk predictions.

### Step 5: Start the Flask Application
```powershell
python app.py
```

### Step 6: Open in Browser
Open your web browser and navigate to:
**[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🧪 Running Unit & System Tests

The test suite validates authentication, role-based protection, parent isolation, multi-child switching, analytics calculations, CSV exports, ML inference, and form validation:

```powershell
python -m unittest tests/test_system.py
```

---

## 📂 Project Architecture

```
EFT Final project/
├── app.py                      # Application entry point & Flask factory
├── config.py                   # Configuration settings & thresholds
├── requirements.txt            # Python dependencies
├── models.py                   # SQLAlchemy database models
├── auth.py                     # Authentication routes & role decorators
├── routes/
│   ├── admin.py                # Admin dashboard & management routes
│   ├── faculty.py              # Faculty dashboard, marks & attendance
│   ├── parent.py               # Parent dashboard & child tracking
│   └── predictions.py          # ML risk APIs & inspection
├── services/
│   ├── analytics.py            # Aggregations, metrics & Chart.js data
│   └── prediction_service.py   # Feature extraction & ML inference
├── ml/
│   ├── train_model.py          # Random Forest training & evaluation
│   └── saved_models/           # Saved joblib model & metrics JSON
├── scripts/
│   └── seed_data.py            # Database initialization & seeding
├── tests/
│   └── test_system.py          # Automated verification test suite
├── templates/
│   ├── base.html               # Main layout with responsive sidebar
│   ├── login.html              # Login page with demo account shortcuts
│   ├── change_password.html    # Password update page
│   ├── error.html              # Custom 403, 404, 500 error pages
│   ├── admin/                  # Admin dashboard & CRUD templates
│   ├── faculty/                # Faculty dashboard & grading templates
│   └── parent/                 # Parent dashboard & feedback templates
├── static/
│   ├── css/style.css           # Navy blue, white, teal UI theme
│   └── js/dashboard.js         # Chart.js initializers & dynamic UI
└── instance/
    └── student_academic.db     # SQLite database
```

---

## 🛡️ Security & Access Control

- **Password Hashing**: Industry-standard Werkzeug scrypt hashing. Plain text passwords are never stored.
- **Route Protection**: All sensitive routes are safeguarded with `@login_required` and role-specific decorators (`@role_required`).
- **Data Scoping**: Faculty can only inspect and grade assigned classes. Parents can only access records belonging to their linked children.
- **CSRF & Validation**: Form inputs validate student IDs, duplicate attendance dates, and numerical mark boundaries.
