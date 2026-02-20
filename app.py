from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Book, Student, BorrowRecord
import os

# Create the flask application instance
app = Flask(__name__)
# Secret key for flash messages and session security
app.config['SECRET_KEY'] = 'library_secret_key_123'
# Configuration for the SQLite database file
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Link the database to the app
db.init_app(app)

# Ensure database tables are created at startup
with app.app_context():
    db.create_all()

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

# Route to add a new book
@app.route('/add_book', methods=['GET', 'POST'])
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
