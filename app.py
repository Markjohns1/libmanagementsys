from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Book, BorrowRecord, User, Notification, AuditLog
import os
import shutil
from datetime import datetime, timedelta
from functools import wraps
from flask import send_file

# Create the flask application instance
app = Flask(__name__)
# Secret key for session security
app.config['SECRET_KEY'] = 'library_secret_key_123'
# Configuration for the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library_v3.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Link the database to the app
db.init_app(app)

# Role-based access control decorator
def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_activity(action, details, user_id=None):
    """Helper to record system activities"""
    if not user_id and current_user and current_user.is_authenticated:
        user_id = current_user.id
    log = AuditLog(user_id=user_id, action=action, details=details)
    db.session.add(log)
    db.session.commit()

# User loader for flask-login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Ensure database tables are created at startup
with app.app_context():
    db.create_all()
    # Create default librarian for testing
    if not User.query.filter_by(username='librarian').first():
        librarian = User(username='librarian', password='lib123', role='librarian', full_name='Jane Doe')
        db.session.add(librarian)
    db.session.commit()

# Route for the Home/Dashboard page
@app.route('/')
def index():
    if current_user.is_authenticated:
        # Fetch notifications for the user
        notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).all()
        
        # Role-specific dashboard stats
        if current_user.role == 'student':
            active_borrows = BorrowRecord.query.filter_by(user_id=current_user.id, return_date=None).count()
            return render_template('index.html', notifications=notifications, active_borrows=active_borrows)
    
    total_books = Book.query.count()
    available_books = Book.query.filter_by(is_available=True).count()
    borrowed_books = total_books - available_books
    return render_template('index.html', 
                           total_books=total_books, 
                           available_books=available_books,
                           borrowed_books=borrowed_books)

# Route to list all books with Search capability
@app.route('/books')
def list_books():
    query = request.args.get('search')
    if query:
        all_books = Book.query.filter(
            (Book.title.contains(query)) | 
            (Book.author.contains(query)) | 
            (Book.isbn.contains(query))
        ).all()
    else:
        all_books = Book.query.all()
    return render_template('books.html', books=all_books)

# Route for Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.password == request.form['password']:
            login_user(user)
            log_activity('LOGIN', f'User {user.username} logged in')
            flash(f'Logged in as {user.role.capitalize()}!', 'success')
            return redirect(url_for('index'))
        flash('Invalid credentials!', 'danger')
    return render_template('login.html')

# Route for Registration (Students only)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
            
        new_user = User(
            username=username,
            password=request.form['password'],
            email=request.form['email'],
            full_name=request.form['full_name'],
            student_id=request.form['student_id'],
            role='student'
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# Route to Logout
@app.route('/logout')
@login_required
def logout():
    log_activity('LOGOUT', f'User {current_user.username} logged out')
    logout_user()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('login'))

# Librarian Routes: Book Management
@app.route('/add_book', methods=['GET', 'POST'])
@login_required
@roles_required('librarian')
def add_book():
    if request.method == 'POST':
        new_book = Book(
            title=request.form['title'],
            author=request.form['author'],
            isbn=request.form['isbn'],
            category=request.form['category']
        )
        db.session.add(new_book)
        db.session.commit()
        log_activity('ADD_BOOK', f'Added book: {new_book.title}')
        flash('Book added successfully!', 'success')
        return redirect(url_for('list_books'))
    return render_template('add_book.html')

@app.route('/edit_book/<int:id>', methods=['GET', 'POST'])
@login_required
@roles_required('librarian')
def edit_book(id):
    book = Book.query.get_or_404(id)
    if request.method == 'POST':
        book.title = request.form['title']
        book.author = request.form['author']
        book.isbn = request.form['isbn']
        book.category = request.form['category']
        db.session.commit()
        flash('Book updated successfully!', 'success')
        return redirect(url_for('list_books'))
    return render_template('edit_book.html', book=book)

@app.route('/delete_book/<int:id>')
@login_required
@roles_required('librarian')
def delete_book(id):
    book = Book.query.get_or_404(id)
    db.session.delete(book)
    db.session.commit()
    flash('Book removed!', 'info')
    return redirect(url_for('list_books'))

# Student/Librarian Routes: Borrowing
@app.route('/borrow/<int:id>', methods=['GET', 'POST'])
@login_required
def borrow_book(id):
    book = Book.query.get_or_404(id)
    if not book.is_available:
        flash('Book is currently unavailable.', 'warning')
        return redirect(url_for('list_books'))
        
    # Students borrow for themselves, Librarians can borrow for others (simplified here as self-borrow)
    due_limit = datetime.utcnow() + timedelta(days=14)
    record = BorrowRecord(
        book_id=book.id, 
        user_id=current_user.id,
        due_date=due_limit
    )
    book.is_available = False
    
    # Notification
    notification = Notification(
        user_id=current_user.id,
        message=f'You have borrowed "{book.title}". Due date: {due_limit.strftime("%Y-%m-%d")}'
    )
    
    db.session.add(record)
    db.session.add(notification)
    db.session.commit()
    log_activity('BORROW', f'Borrowed: {book.title}')
    flash(f'Successfully borrowed "{book.title}"!', 'success')
    return redirect(url_for('index'))

@app.route('/return/<int:id>')
@login_required
def return_book(id):
    record = BorrowRecord.query.filter_by(book_id=id, return_date=None).first()
    if not record:
        flash('No active borrow record found for this book.', 'warning')
        return redirect(url_for('list_books'))
    
    # Students can ONLY return books they personally borrowed
    if current_user.role == 'student' and record.user_id != current_user.id:
        flash('You can only return books you borrowed.', 'danger')
        return redirect(url_for('list_books'))
    
    # Librarians can return any book
    record.return_date = datetime.utcnow()
    record.book.is_available = True
    
    notification = Notification(
        user_id=record.user_id,
        message=f'You have returned "{record.book.title}".'
    )
    db.session.add(notification)
    db.session.commit()
    log_activity('RETURN', f'Returned: {record.book.title} (by {record.user.full_name})')
    flash('Book returned successfully!', 'success')
    return redirect(url_for('list_books'))

# Route for User History
@app.route('/history')
@login_required
def view_history():
    if current_user.role == 'student':
        history = BorrowRecord.query.filter_by(user_id=current_user.id).order_by(BorrowRecord.borrow_date.desc()).all()
    else:
        history = BorrowRecord.query.order_by(BorrowRecord.borrow_date.desc()).all()
    return render_template('history.html', history=history)

# --- LIBRARIAN: USER MANAGEMENT ---
@app.route('/users')
@login_required
@roles_required('librarian')
def manage_users():
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/edit_user/<int:id>', methods=['GET', 'POST'])
@login_required
@roles_required('librarian')
def edit_user(id):
    user = User.query.get_or_404(id)
    if request.method == 'POST':
        user.full_name = request.form['full_name']
        user.role = request.form['role']
        db.session.commit()
        log_activity('USER_MGMT', f'Edited user: {user.username} (Role: {user.role})')
        flash('User updated successfully!', 'success')
        return redirect(url_for('manage_users'))
    return render_template('edit_user.html', user=user)

@app.route('/delete_user/<int:id>')
@login_required
@roles_required('librarian')
def delete_user(id):
    if current_user.id == id:
        flash('You cannot delete yourself!', 'danger')
        return redirect(url_for('manage_users'))
    user = User.query.get_or_404(id)
    username = user.username
    db.session.delete(user)
    db.session.commit()
    log_activity('USER_MGMT', f'Deleted user: {username}')
    flash('User deleted!', 'info')
    return redirect(url_for('manage_users'))

# --- LIBRARIAN: MONITORING & TOOLS ---
@app.route('/monitoring')
@login_required
@roles_required('librarian')
def monitoring():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('monitoring.html', logs=logs)

@app.route('/backup')
@login_required
@roles_required('librarian')
def backup_data():
    db_path = 'instance/library_v3.db' if os.path.exists('instance/library_v3.db') else 'library_v3.db'
    backup_path = f'backup_library_{datetime.now().strftime("%Y%m%d_%H%M")}.db'
    try:
        shutil.copy2(db_path, backup_path)
        log_activity('BACKUP', f'System backup created: {backup_path}')
        return send_file(backup_path, as_attachment=True)
    except Exception as e:
        flash(f'Backup failed: {str(e)}', 'danger')
        return redirect(url_for('index'))

# Start the application in debug mode
@app.context_processor
def inject_now():
    return {'datetime_now': datetime.utcnow()}

if __name__ == '__main__':
    app.run(debug=True)

