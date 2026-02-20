from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Book, Student, BorrowRecord, User
import os

# Create the flask application instance
app = Flask(__name__)
# Secret key for session security
app.config['SECRET_KEY'] = 'library_secret_key_123'
# Configuration for the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Link the database to the app
db.init_app(app)

# User loader for flask-login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Ensure database tables are created at startup
with app.app_context():
    db.create_all()
    # Create a default admin user for the student to test with
    if not User.query.filter_by(username='admin').first():
        default_admin = User(username='admin', password='password')
        db.session.add(default_admin)
        db.session.commit()

# Route for the Home/Dashboard page
@app.route('/')
def index():
    # Fetch counts for the dashboard
    total_books = Book.query.count()
    available_books = Book.query.filter_by(is_available=True).count()
    return render_template('index.html', total_books=total_books, available_books=available_books)

# Route to list all books
@app.route('/books')
def list_books():
    all_books = Book.query.all()
    return render_template('books.html', books=all_books)

# Route for Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Simple student-level authentication logic
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.password == request.form['password']:
            login_user(user)
            flash('Admin Logged in successfully!')
            return redirect(url_for('index'))
        flash('Invalid credentials!')
    return render_template('login.html')

# Route to Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!')
    return redirect(url_for('login'))

# Route to add a new book (Protected)
@app.route('/add_book', methods=['GET', 'POST'])
@login_required
def add_book():
    if request.method == 'POST':
        # Create new book from form data
        new_book = Book(
            title=request.form['title'],
            author=request.form['author'],
            isbn=request.form['isbn']
        )
        db.session.add(new_book)
        db.session.commit()
        flash('Book added successfully!')
        return redirect(url_for('list_books'))
    return render_template('add_book.html')

# Start the application in debug mode
if __name__ == '__main__':
    app.run(debug=True)
