from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Initialize the database object
db = SQLAlchemy()

class User(db.Model, UserMixin):
    # Model for Admin/Staff login
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Book(db.Model):
    # Primary key for each book
    id = db.Column(db.Integer, primary_key=True)
    # Book details
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=False)
    # Track availability
    is_available = db.Column(db.Boolean, default=True)

class Student(db.Model):
    # Unique ID for each student
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    student_id = db.Column(db.String(20), unique=True, nullable=False)

class BorrowRecord(db.Model):
    # Log for tracking who took which book and when
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    # Date tracking
    borrow_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=False)
    return_date = db.Column(db.DateTime, nullable=True)
    
    # Relationships for easy access
    book = db.relationship('Book', backref='borrows')
    student = db.relationship('Student', backref='borrows')
