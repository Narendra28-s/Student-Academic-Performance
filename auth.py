from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from models import db, User

auth_bp = Blueprint('auth', __name__)

def get_current_user():
    """Returns the current User object from session, or None."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return db.session.get(User, user_id)

def login_required(view_func):
    @wraps(view_func)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        user = get_current_user()
        if not user or not user.is_active:
            session.clear()
            flash('Your account has been deactivated or not found. Please contact administration.', 'danger')
            return redirect(url_for('auth.login'))
            
        g.current_user = user
        return view_func(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            
            user_role = session.get('user_role')
            if user_role not in allowed_roles:
                flash(f'Access denied. You do not have permission to view that resource ({user_role} role not permitted).', 'danger')
                if user_role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif user_role == 'faculty':
                    return redirect(url_for('faculty.dashboard'))
                elif user_role == 'parent':
                    return redirect(url_for('parent.dashboard'))
                return redirect(url_for('auth.login'))
                
            return view_func(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        role = session.get('user_role')
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'faculty':
            return redirect(url_for('faculty.dashboard'))
        elif role == 'parent':
            return redirect(url_for('parent.dashboard'))
            
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        selected_role = request.form.get('role', '').strip().lower()
        
        if not email or not password:
            flash('Please enter both email address and password.', 'danger')
            return render_template('login.html', email=email, selected_role=selected_role)
            
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            flash('Invalid email or password. Please try again.', 'danger')
            return render_template('login.html', email=email, selected_role=selected_role)
            
        if not user.is_active:
            flash('This account has been deactivated. Please contact administrator.', 'danger')
            return render_template('login.html', email=email, selected_role=selected_role)
            
        if selected_role and selected_role != user.role:
            flash(f'Role mismatch: Account exists as "{user.role.title()}", but you selected "{selected_role.title()}".', 'warning')
            return render_template('login.html', email=email, selected_role=selected_role)
            
        # Session setup
        session.clear()
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['user_name'] = user.full_name
        session['user_role'] = user.role
        session.permanent = True
        
        flash(f'Welcome back, {user.full_name}!', 'success')
        
        next_url = request.args.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
            
        if user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user.role == 'faculty':
            return redirect(url_for('faculty.dashboard'))
        elif user.role == 'parent':
            return redirect(url_for('parent.dashboard'))
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been successfully logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    user = get_current_user()
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not user.check_password(current_password):
            flash('Current password is incorrect.', 'danger')
        elif len(new_password) < 6:
            flash('New password must be at least 6 characters long.', 'danger')
        elif new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
        else:
            user.set_password(new_password)
            db.session.commit()
            flash('Your password has been updated successfully!', 'success')
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'faculty':
                return redirect(url_for('faculty.dashboard'))
            return redirect(url_for('parent.dashboard'))
            
    return render_template('change_password.html', user=user)
