# Importing the necessary modules
from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Setting up the Flask app
app = Flask(__name__)
app.secret_key = 'e1a139751d4d7926bb9d4d1faea91a0ffcdc05321a54d750'

# Setting up the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo_app.db'  # Specify database file name
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    tasks = db.relationship('Todo', backref='user', lazy=True)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

# Define the Todo model
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Task {self.id}>'

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Route for the home page
@app.route('/index', methods=['POST', 'GET'])
@login_required
def index():
    error_message = session.pop('error_message', None)  # Retrieve and clear the error message

    if request.method == 'POST':
        task_content = request.form.get('content')
        if task_content and task_content.strip():
            new_task = Todo(content=task_content.strip(), user=current_user)
            try:
                db.session.add(new_task)
                db.session.commit()
                return redirect('/index')
            except Exception as e:
                session['error_message'] = f'There was an issue adding your task: {e}'
        else:
            session['error_message'] = 'Task content cannot be empty'
    
    tasks = current_user.tasks
    return render_template('index.html', tasks=tasks, error_message=error_message)

# Route for deleting a task
@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    task_to_delete = Todo.query.get_or_404(id)
    if task_to_delete.user != current_user:
        session['error_message'] = 'You can only delete your own tasks.'
        return redirect('/index')
    try:
        db.session.delete(task_to_delete)
        db.session.commit()
        return redirect('/index')
    except Exception as e:
        session['error_message'] = f'There was a problem deleting the task: {e}'
        return redirect('/index')

# Route for updating a task
@app.route('/update/<int:id>', methods=['GET', 'POST'])
@login_required
def update(id):
    task = Todo.query.get_or_404(id)
    if task.user != current_user:
        session['error_message'] = 'You can only update your own tasks.'
        return redirect('/index')

    if request.method == 'POST':
        task_content = request.form.get('content')
        if task_content and task_content.strip():
            task.content = task_content.strip()
            try:
                db.session.commit()
                return redirect('/index')
            except Exception as e:
                session['error_message'] = f'There was an issue updating your task: {e}'
        else:
            session['error_message'] = 'Task content cannot be empty'
    return render_template('update.html', task=task, error_message=session.pop('error_message', None))

# Route for the login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = session.pop('error_message', None)

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or '/index')

        session['error_message'] = 'Invalid username or password.'
        return redirect('/login')
    
    return render_template('login.html', error_message=error_message)

# Route for registering a new user
@app.route('/register', methods=['GET', 'POST'])
def register():
    error_message = session.pop('error_message', None)

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            session['error_message'] = 'Both username and password are required.'
            return redirect('/register')

        if User.query.filter_by(username=username).first():
            session['error_message'] = 'Username is already taken.'
            return redirect('/register')

        new_user = User(username=username)
        new_user.set_password(password)
        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect('/login')
        except Exception as e:
            session['error_message'] = f'There was an issue registering the user: {e}'
            return redirect('/register')

    return render_template('register.html', error_message=error_message)

# Route for logging out
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

# Default route redirect
@app.route('/')
def root():
    if current_user.is_authenticated:
        return redirect('/index')
    return redirect('/login')

# Initialize database before running
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
