from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Initialize the database object
db = SQLAlchemy()

class User(db.Model, UserMixin):
    # Model for all users: Students and Librarians
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student') # student, librarian
    
    # Profile info (relevant for students)
    full_name = db.Column(db.String(100), nullable=False)
    student_id = db.Column(db.String(20), unique=True, nullable=True) # Only for students
    
    # Relationships
    borrows = db.relationship('BorrowRecord', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)

class Book(db.Model):
    # Primary key for each book
    id = db.Column(db.Integer, primary_key=True)
    # Book details
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=True)
    # Track availability
    is_available = db.Column(db.Boolean, default=True)

class BorrowRecord(db.Model):
    # Log for tracking who took which book and when
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Date tracking
    borrow_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=False)
    return_date = db.Column(db.DateTime, nullable=True)
    
    # Relationship for EASY access to book details
    book = db.relationship('Book', backref='borrows')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # None for system events
    action = db.Column(db.String(100), nullable=False) # e.g., 'LOGIN', 'BORROW', 'ADD_BOOK', 'USER_MANAGEMENT'
    details = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship for viewing user in monitoring
    user = db.relationship('User', backref='logs')

