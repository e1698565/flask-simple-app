from flask import Flask, request, redirect, url_for, session, flash, get_flashed_messages, Response
from functools import wraps
import hashlib
import secrets
from datetime import datetime
import mysql.connector
from mysql.connector import Error
import csv
from io import StringIO
import sqlparse
import time

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'sql_grader',
    'user': 'root',
    'password': 'root',  # Your MySQL password
    'port': 3306
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Database error: {e}")
        return None

# Enhanced AutoGrader class
class AutoGrader:
    def grade_submission(self, student_sql, model_sql):
        """Grade a single SQL submission"""
        student_normalized = student_sql.lower().strip().rstrip(';')
        model_normalized = model_sql.lower().strip().rstrip(';')
        
        # Calculate simple similarity
        if student_normalized == model_normalized:
            score = 100
            feedback = "Perfect! Your solution matches exactly."
        elif student_normalized in model_normalized or model_normalized in student_normalized:
            score = 85
            feedback = "Good! Close to the model answer."
        else:
            # Check for keywords
            keywords = ['select', 'from', 'where', 'join', 'insert', 'update', 'delete']
            matched = sum(1 for kw in keywords if kw in student_normalized)
            score = min(50 + matched * 10, 80)
            feedback = f"Partial match. Score: {score}/100"
        
        return score, feedback
    
    def grade_multiple_statements(self, student_sql, model_sqls):
        """Grade multiple SQL statements"""
        try:
            # Split student submission into statements
            statements = [s.strip() for s in sqlparse.split(student_sql) if s.strip()]
            
            if len(statements) != len(model_sqls):
                return 50, f"Statement count mismatch: Expected {len(model_sqls)}, got {len(statements)}"
            
            total_score = 0
            all_feedback = []
            
            for i, (stmt, model) in enumerate(zip(statements, model_sqls), 1):
                score, feedback = self.grade_submission(stmt, model)
                total_score += score
                all_feedback.append(f"Statement {i}: {feedback} (Score: {score}/100)")
            
            avg_score = total_score // len(model_sqls)
            return avg_score, "\n".join(all_feedback)
            
        except Exception as e:
            return 0, f"Error grading multiple statements: {str(e)}"

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Global CSS styles
GLOBAL_CSS = """
<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
        padding: 20px;
    }
    
    .container {
        max-width: 1400px;
        margin: 0 auto;
        background: white;
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        overflow: hidden;
        animation: fadeIn 0.5s ease-in;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .content {
        padding: 30px;
    }
    
    nav {
        background: linear-gradient(135deg, #2c3e50 0%, #1a1a2e 100%);
        padding: 15px 30px;
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        border-bottom: 3px solid #667eea;
    }
    
    nav a {
        color: white;
        text-decoration: none;
        padding: 10px 20px;
        border-radius: 25px;
        transition: all 0.3s ease;
        font-weight: 500;
        background: rgba(255,255,255,0.1);
    }
    
    nav a:hover {
        background: #667eea;
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    
    h1 {
        color: #2c3e50;
        margin-bottom: 20px;
        font-size: 2em;
        border-left: 5px solid #667eea;
        padding-left: 20px;
    }
    
    h2 {
        color: #34495e;
        margin: 20px 0 15px 0;
        font-size: 1.5em;
    }
    
    h3 {
        color: #555;
        margin: 15px 0 10px 0;
    }
    
    .score-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        margin: 20px 0;
        background: white;
        border-radius: 15px;
        overflow: hidden;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    
    .score-table thead tr {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    .score-table th {
        padding: 15px;
        text-align: left;
        font-weight: 600;
        font-size: 0.9em;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .score-table td {
        padding: 15px;
        border-bottom: 1px solid #e0e0e0;
    }
    
    .score-table tbody tr {
        transition: all 0.3s ease;
    }
    
    .score-table tbody tr:hover {
        background: #f8f9ff;
        transform: scale(1.01);
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .score-badge {
        display: inline-block;
        padding: 8px 15px;
        border-radius: 30px;
        font-weight: bold;
        font-size: 1.1em;
        text-align: center;
        min-width: 80px;
        transition: all 0.3s ease;
    }
    
    .score-excellent {
        background: linear-gradient(135deg, #00b09b, #96c93d);
        color: white;
        box-shadow: 0 2px 10px rgba(0,176,155,0.3);
    }
    
    .score-good {
        background: linear-gradient(135deg, #2193b0, #6dd5ed);
        color: white;
        box-shadow: 0 2px 10px rgba(33,147,176,0.3);
    }
    
    .score-average {
        background: linear-gradient(135deg, #f2994a, #f2c94c);
        color: white;
        box-shadow: 0 2px 10px rgba(242,153,74,0.3);
    }
    
    .score-low {
        background: linear-gradient(135deg, #eb3349, #f45c43);
        color: white;
        box-shadow: 0 2px 10px rgba(235,51,73,0.3);
    }
    
    .score-fail {
        background: linear-gradient(135deg, #7f00ff, #e100ff);
        color: white;
        box-shadow: 0 2px 10px rgba(127,0,255,0.3);
    }
    
    .score-container {
        display: flex;
        align-items: center;
        gap: 15px;
        flex-wrap: wrap;
    }
    
    .score-bar {
        flex: 1;
        height: 10px;
        background: #e0e0e0;
        border-radius: 10px;
        overflow: hidden;
        min-width: 150px;
    }
    
    .score-bar-fill {
        height: 100%;
        border-radius: 10px;
        transition: width 0.5s ease;
    }
    
    .score-bar-fill.excellent { background: linear-gradient(90deg, #00b09b, #96c93d); }
    .score-bar-fill.good { background: linear-gradient(90deg, #2193b0, #6dd5ed); }
    .score-bar-fill.average { background: linear-gradient(90deg, #f2994a, #f2c94c); }
    .score-bar-fill.low { background: linear-gradient(90deg, #eb3349, #f45c43); }
    .score-bar-fill.fail { background: linear-gradient(90deg, #7f00ff, #e100ff); }
    
    .attempt-badge {
        display: inline-block;
        padding: 5px 12px;
        background: #f0f0f0;
        border-radius: 20px;
        font-size: 0.85em;
        font-weight: bold;
        color: #555;
    }
    
    .attempt-badge.best {
        background: #ffd700;
        color: #333;
        box-shadow: 0 2px 5px rgba(255,215,0,0.3);
    }
    
    .summary-cards {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
        margin: 30px 0;
    }
    
    .card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
        text-align: center;
    }
    
    .card:hover {
        transform: translateY(-5px);
    }
    
    .card h4 {
        color: #666;
        font-size: 0.85em;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 10px;
    }
    
    .card .value {
        font-size: 2.5em;
        font-weight: bold;
        color: #2c3e50;
    }
    
    .form-group {
        margin-bottom: 20px;
    }
    
    label {
        display: block;
        margin-bottom: 8px;
        font-weight: 600;
        color: #333;
    }
    
    input[type="text"],
    input[type="password"],
    select,
    textarea {
        width: 100%;
        padding: 12px;
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        font-size: 14px;
        transition: all 0.3s ease;
    }
    
    input:focus,
    select:focus,
    textarea:focus {
        outline: none;
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
    }
    
    button {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        padding: 12px 30px;
        border: none;
        border-radius: 30px;
        cursor: pointer;
        font-size: 16px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(102,126,234,0.4);
    }
    
    .alert {
        padding: 15px 20px;
        margin-bottom: 20px;
        border-radius: 10px;
        animation: slideIn 0.3s ease;
    }
    
    @keyframes slideIn {
        from { transform: translateX(-100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    .alert-success {
        background: #d4edda;
        color: #155724;
        border-left: 5px solid #28a745;
    }
    
    .alert-error {
        background: #f8d7da;
        color: #721c24;
        border-left: 5px solid #dc3545;
    }
    
    .alert-info {
        background: #d1ecf1;
        color: #0c5460;
        border-left: 5px solid #17a2b8;
    }
    
    .info-box {
        margin-top: 20px;
        padding: 15px;
        background: #e7f3ff;
        border-radius: 10px;
        border-left: 5px solid #667eea;
    }
    
    .example {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin-top: 20px;
        font-family: monospace;
    }
    
    @media (max-width: 768px) {
        .container {
            border-radius: 10px;
        }
        
        nav {
            flex-direction: column;
        }
        
        nav a {
            text-align: center;
        }
        
        .score-table {
            font-size: 12px;
        }
        
        .score-table th,
        .score-table td {
            padding: 10px 8px;
        }
        
        .score-badge {
            padding: 4px 8px;
            font-size: 0.85em;
            min-width: 60px;
        }
        
        .summary-cards {
            grid-template-columns: 1fr;
        }
    }
</style>
"""

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hash_password(request.form['password'])
        
        conn = get_db_connection()
        if not conn:
            flash('Database connection error', 'error')
            return redirect(url_for('login'))
            
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT * FROM students WHERE username = %s AND password_hash = %s"
        cursor.execute(query, (username, password))
        student = cursor.fetchone()
        
        if student:
            session['username'] = username
            flash('Login successful!', 'success')
            cursor.close()
            conn.close()
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
        
        cursor.close()
        conn.close()
    
    # Get flashed messages
    messages = get_flashed_messages(with_categories=True)
    messages_html = ''
    for category, message in messages:
        messages_html += f'<div class="alert alert-{category}">{message}</div>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login - SQL Grader</title>
        {GLOBAL_CSS}
    </head>
    <body>
        <div class="container">
            <div class="content">
                <h1>📚 SQL Assignment Grader</h1>
                <h2>Login</h2>
                {messages_html}
                <form method="POST">
                    <div class="form-group">
                        <label>Username:</label>
                        <input type="text" name="username" required>
                    </div>
                    <div class="form-group">
                        <label>Password:</label>
                        <input type="password" name="password" required>
                    </div>
                    <button type="submit">Login</button>
                </form>
                <div class="info-box">
                    <strong>Test Credentials:</strong><br>
                    Username: test_student<br>
                    Password: password123
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/home')
@login_required
def home():
    messages = get_flashed_messages(with_categories=True)
    messages_html = ''
    for category, message in messages:
        messages_html += f'<div class="alert alert-{category}">{message}</div>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Home - SQL Grader</title>
        {GLOBAL_CSS}
    </head>
    <body>
        <div class="container">
            <nav>
                <a href="/home">🏠 Home</a>
                <a href="/submit">📝 Submit SQL</a>
                <a href="/submit_multiple">📚 Submit Multiple SQL</a>
                <a href="/scores">📊 My Scores</a>
                <a href="/leaderboard">🏆 Leaderboard</a>
                <a href="/change_password">🔑 Change Password</a>
                <a href="/export_csv">📥 Export CSV</a>
                <a href="/admin/due_date">⚙️ Admin</a>
                <a href="/login">🚪 Logout</a>
            </nav>
            <div class="content">
                {messages_html}
                <div class="info-box">
                    <h2>Welcome, {session['username']}! 👋</h2>
                    <p>Ready to test your SQL skills? Submit your solutions and get instant feedback!</p>
                </div>
                <h3>Quick Actions:</h3>
                <ul>
                    <li><a href="/submit">📤 Submit single SQL solution</a></li>
                    <li><a href="/submit_multiple">📚 Submit multiple SQL statements</a></li>
                    <li><a href="/scores">📈 View your grading history</a></li>
                    <li><a href="/leaderboard">🏅 Check how you rank</a></li>
                    <li><a href="/export_csv">💾 Download your scores as CSV</a></li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/submit', methods=['GET', 'POST'])
@login_required
def submit():
    if request.method == 'POST':
        aid = request.form.get('aid')
        tid = request.form.get('tid')
        sql_code = request.form.get('sql_code')
        
        if not aid or not tid or not sql_code:
            flash('Please fill in all fields', 'error')
            return redirect(url_for('submit'))
        
        conn = get_db_connection()
        if not conn:
            flash('Database connection error', 'error')
            return redirect(url_for('submit'))
            
        cursor = conn.cursor(dictionary=True)
        
        task_query = """
            SELECT t.*, a.due_date 
            FROM tasks t
            JOIN assessments a ON t.aid = a.aid
            WHERE t.tid = %s
        """
        cursor.execute(task_query, (tid,))
        task = cursor.fetchone()
        
        if task:
            attempt_query = "SELECT MAX(attempt_number) as max_attempt FROM submissions WHERE username = %s AND tid = %s"
            cursor.execute(attempt_query, (session['username'], tid))
            result = cursor.fetchone()
            attempt_number = (result['max_attempt'] or 0) + 1
            
            grader = AutoGrader()
            score, feedback = grader.grade_submission(sql_code, task['model_answer'])
            original_score = score
            
            submit_time = datetime.now()
            if submit_time > task['due_date']:
                score = int(score * 0.9)
                feedback += f"\n\n⚠️ LATE SUBMISSION PENALTY: 10% applied. Original score: {original_score}, Final score: {score}"
            
            insert_query = """
                INSERT INTO submissions (username, aid, tid, code, submit_at, attempt_number, score, feedback)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (session['username'], aid, tid, sql_code, submit_time, attempt_number, score, feedback))
            conn.commit()
            
            flash(f'✅ Submission graded! Score: {score}/100', 'success')
            flash(feedback, 'info')
        else:
            flash('Invalid task ID', 'error')
        
        cursor.close()
        conn.close()
        return redirect(url_for('scores'))
    
    messages = get_flashed_messages(with_categories=True)
    messages_html = ''
    for category, message in messages:
        messages_html += f'<div class="alert alert-{category}">{message}</div>'
    
    conn = get_db_connection()
    tasks_html = '<select name="tid" required><option value="">Select a task</option>'
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT t.tid, a.aid, a.title as assessment_title, t.title as task_title
            FROM tasks t
            JOIN assessments a ON t.aid = a.aid
        """)
        tasks = cursor.fetchall()
        for task in tasks:
            tasks_html += f'<option value="{task["tid"]}">{task["assessment_title"]} - {task["task_title"]}</option>'
        cursor.close()
        conn.close()
    tasks_html += '</select>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Submit SQL - SQL Grader</title>
        {GLOBAL_CSS}
    </head>
    <body>
        <div class="container">
            <nav>
                <a href="/home">🏠 Home</a>
                <a href="/submit">📝 Submit SQL</a>
                <a href="/submit_multiple">📚 Submit Multiple SQL</a>
                <a href="/scores">📊 My Scores</a>
                <a href="/leaderboard">🏆 Leaderboard</a>
                <a href="/change_password">🔑 Change Password</a>
                <a href="/export_csv">📥 Export CSV</a>
                <a href="/admin/due_date">⚙️ Admin</a>
                <a href="/login">🚪 Logout</a>
            </nav>
            <div class="content">
                <h1>📝 Submit SQL Solution</h1>
                <a href="/home">← Back to Home</a>
                {messages_html}
                <form method="POST">
                    <div class="form-group">
                        <label>Assessment ID (aid):</label>
                        <input type="text" name="aid" placeholder="e.g., 1" required>
                    </div>
                    <div class="form-group">
                        <label>Task:</label>
                        {tasks_html}
                    </div>
                    <div class="form-group">
                        <label>SQL Code:</label>
                        <textarea name="sql_code" placeholder="Enter your SQL query here..." required></textarea>
                    </div>
                    <button type="submit">Submit for Grading</button>
                </form>
                <div class="info-box">
                    <strong>💡 Tip:</strong> Submissions after the due date will receive a 10% penalty.
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/submit_multiple', methods=['GET', 'POST'])
@login_required
def submit_multiple():
    if request.method == 'POST':
        aid = request.form.get('aid')
        tid = request.form.get('tid')
        sql_code = request.form.get('sql_code')
        
        if not aid or not tid or not sql_code:
            flash('Please fill in all fields', 'error')
            return redirect(url_for('submit_multiple'))
        
        conn = get_db_connection()
        if not conn:
            flash('Database connection error', 'error')
            return redirect(url_for('submit_multiple'))
            
        cursor = conn.cursor(dictionary=True)
        
        task_query = """
            SELECT t.*, a.due_date 
            FROM tasks t
            JOIN assessments a ON t.aid = a.aid
            WHERE t.tid = %s
        """
        cursor.execute(task_query, (tid,))
        task = cursor.fetchone()
        
        if task:
            model_statements = [s.strip() for s in sqlparse.split(task['model_answer']) if s.strip()]
            
            attempt_query = "SELECT MAX(attempt_number) as max_attempt FROM submissions WHERE username = %s AND tid = %s"
            cursor.execute(attempt_query, (session['username'], tid))
            result = cursor.fetchone()
            attempt_number = (result['max_attempt'] or 0) + 1
            
            grader = AutoGrader()
            if len(model_statements) > 1:
                score, feedback = grader.grade_multiple_statements(sql_code, model_statements)
            else:
                score, feedback = grader.grade_submission(sql_code, task['model_answer'])
            
            original_score = score
            
            submit_time = datetime.now()
            if submit_time > task['due_date']:
                score = int(score * 0.9)
                feedback += f"\n\n⚠️ LATE SUBMISSION PENALTY: 10% applied. Original score: {original_score}, Final score: {score}"
            
            insert_query = """
                INSERT INTO submissions (username, aid, tid, code, submit_at, attempt_number, score, feedback)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (session['username'], aid, tid, sql_code, submit_time, attempt_number, score, feedback))
            conn.commit()
            
            flash(f'✅ Multiple statements submission graded! Score: {score}/100', 'success')
            flash(feedback, 'info')
        else:
            flash('Invalid task ID', 'error')
        
        cursor.close()
        conn.close()
        return redirect(url_for('scores'))
    
    messages = get_flashed_messages(with_categories=True)
    messages_html = ''
    for category, message in messages:
        messages_html += f'<div class="alert alert-{category}">{message}</div>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Submit Multiple SQL - SQL Grader</title>
        {GLOBAL_CSS}
    </head>
    <body>
        <div class="container">
            <nav>
                <a href="/home">🏠 Home</a>
                <a href="/submit">📝 Submit SQL</a>
                <a href="/submit_multiple">📚 Submit Multiple SQL</a>
                <a href="/scores">📊 My Scores</a>
                <a href="/leaderboard">🏆 Leaderboard</a>
                <a href="/change_password">🔑 Change Password</a>
                <a href="/export_csv">📥 Export CSV</a>
                <a href="/admin/due_date">⚙️ Admin</a>
                <a href="/login">🚪 Logout</a>
            </nav>
            <div class="content">
                <h1>📚 Submit Multiple SQL Statements</h1>
                <a href="/home">← Back to Home</a>
                {messages_html}
                <form method="POST">
                    <div class="form-group">
                        <label>Assessment ID (aid):</label>
                        <input type="text" name="aid" placeholder="e.g., 1" required>
                    </div>
                    <div class="form-group">
                        <label>Task ID (tid):</label>
                        <input type="text" name="tid" placeholder="e.g., 1" required>
                    </div>
                    <div class="form-group">
                        <label>SQL Code (multiple statements):</label>
                        <textarea name="sql_code" placeholder="Enter multiple SQL statements separated by semicolons...&#10;&#10;Example:&#10;INSERT INTO students VALUES ('demo1', 'demo1@nowhere.com', 2025);&#10;UPDATE students SET department = 'Computer Science' WHERE department = 'CS';" required></textarea>
                    </div>
                    <button type="submit">Submit Multiple Statements for Grading</button>
                </form>
                <div class="example">
                    <strong>📝 Example for Demo Step 4:</strong><br>
                    Task: Add a new student and update CS students' department<br>
                    <strong>Partially correct submission:</strong><br>
                    <code>
                    INSERT INTO students VALUES ('demo1', 'demo1@nowhere.com', 2025, 'Math', 'Science', NULL);<br>
                    UPDATE students SET department = 'Computer Science';
                    </code>
                    <br><br>
                    <strong>Note:</strong> The UPDATE is missing a WHERE clause, making it only partially correct.
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/scores')
@login_required
def scores():
    conn = get_db_connection()
    if not conn:
        return "Database error", 500
        
    cursor = conn.cursor(dictionary=True)
    
    scores_query = """
        SELECT s.submission_id, s.username, s.aid, s.tid, s.code, 
               s.submit_at, s.attempt_number, s.score, s.feedback,
               a.title as assessment_title, 
               t.title as task_title
        FROM submissions s
        JOIN assessments a ON s.aid = a.aid
        JOIN tasks t ON s.tid = t.tid
        WHERE s.username = %s
        ORDER BY s.submit_at DESC
    """
    cursor.execute(scores_query, (session['username'],))
    submissions = cursor.fetchall()
    
    if submissions:
        scores_list = [s['score'] for s in submissions]
        best_score = max(scores_list)
        avg_score = sum(scores_list) / len(scores_list)
        total_attempts = len(submissions)
        unique_tasks = len(set(s['tid'] for s in submissions))
    else:
        best_score = 0
        avg_score = 0
        total_attempts = 0
        unique_tasks = 0
    
    cursor.close()
    conn.close()
    
    if not submissions:
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>My Scores</title>
            {GLOBAL_CSS}
        </head>
        <body>
            <div class="container">
                <nav>
                    <a href="/home">🏠 Home</a>
                    <a href="/submit">📝 Submit SQL</a>
                    <a href="/submit_multiple">📚 Submit Multiple SQL</a>
                    <a href="/scores">📊 My Scores</a>
                    <a href="/leaderboard">🏆 Leaderboard</a>
                    <a href="/change_password">🔑 Change Password</a>
                    <a href="/export_csv">📥 Export CSV</a>
                    <a href="/admin/due_date">⚙️ Admin</a>
                    <a href="/login">🚪 Logout</a>
                </nav>
                <div class="content">
                    <h1>📊 My Scores</h1>
                    <a href="/home">← Back to Home</a>
                    <p>No submissions yet. <a href="/submit">Submit your first SQL solution!</a></p>
                </div>
            </div>
        </body>
        </html>
        '''
    
    rows = ''
    for sub in submissions:
        if sub['score'] >= 90:
            score_class = "score-excellent"
            score_label = "A+"
        elif sub['score'] >= 80:
            score_class = "score-good"
            score_label = "A"
        elif sub['score'] >= 70:
            score_class = "score-average"
            score_label = "B"
        elif sub['score'] >= 60:
            score_class = "score-average"
            score_label = "C"
        elif sub['score'] >= 50:
            score_class = "score-low"
            score_label = "D"
        else:
            score_class = "score-fail"
            score_label = "F"
        
        is_best = sub['score'] == best_score and sub['score'] >= 80
        submit_date = sub['submit_at'].strftime('%Y-%m-%d %H:%M:%S') if sub['submit_at'] else 'N/A'
        
        rows += f'''
        <tr>
            <td><strong>{sub['assessment_title']}</strong></td>
            <td>{sub['task_title']}</td>
            <td>{submit_date}</td>
            <td><span class="attempt-badge {'best' if is_best else ''}">#{sub['attempt_number']}</span></td>
            <td>
                <div class="score-container">
                    <span class="score-badge {score_class}">{sub['score']}/100 ({score_label})</span>
                    <div class="score-bar">
                        <div class="score-bar-fill {score_class.replace('score-', '')}" style="width: {sub['score']}%"></div>
                    </div>
                </div>
            </td>
        </tr>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>My Scores - SQL Grader</title>
        {GLOBAL_CSS}
    </head>
    <body>
        <div class="container">
            <nav>
                <a href="/home">🏠 Home</a>
                <a href="/submit">📝 Submit SQL</a>
                <a href="/submit_multiple">📚 Submit Multiple SQL</a>
                <a href="/scores">📊 My Scores</a>
                <a href="/leaderboard">🏆 Leaderboard</a>
                <a href="/change_password">🔑 Change Password</a>
                <a href="/export_csv">📥 Export CSV</a>
                <a href="/admin/due_date">⚙️ Admin</a>
                <a href="/login">🚪 Logout</a>
            </nav>
            <div class="content">
                <h1>📊 My Scores Dashboard</h1>
                <a href="/home">← Back to Home</a>
                <a href="/export_csv" style="margin-left: 20px;">📥 Export to CSV</a>
                
                <div class="summary-cards">
                    <div class="card">
                        <h4>🏆 Best Score</h4>
                        <div class="value">{best_score}/100</div>
                        <small>Highest achieved</small>
                    </div>
                    <div class="card">
                        <h4>📊 Average Score</h4>
                        <div class="value">{avg_score:.1f}/100</div>
                        <small>Overall performance</small>
                    </div>
                    <div class="card">
                        <h4>📝 Total Attempts</h4>
                        <div class="value">{total_attempts}</div>
                        <small>Submissions made</small>
                    </div>
                    <div class="card">
                        <h4>✅ Tasks Completed</h4>
                        <div class="value">{unique_tasks}</div>
                        <small>Distinct tasks</small>
                    </div>
                </div>
                
                <h2>📋 Submission History</h2>
                <table class="score-table">
                    <thead>
                        <tr>
                            <th>Assessment</th>
                            <th>Task</th>
                            <th>Submission Date</th>
                            <th>Attempt</th>
                            <th>Score</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
                
                <div class="info-box">
                    <h4>📖 Score Legend</h4>
                    <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-top: 10px;">
                        <div><span class="score-badge score-excellent" style="font-size: 0.8em;">90-100</span> Excellent (A+)</div>
                        <div><span class="score-badge score-good" style="font-size: 0.8em;">80-89</span> Good (A)</div>
                        <div><span class="score-badge score-average" style="font-size: 0.8em;">60-79</span> Average (B-C)</div>
                        <div><span class="score-badge score-low" style="font-size: 0.8em;">50-59</span> Low (D)</div>
                        <div><span class="score-badge score-fail" style="font-size: 0.8em;">0-49</span> Fail (F)</div>
                    </div>
                    <div style="margin-top: 10px;">
                        <span class="attempt-badge best">★</span> Best attempt for this task
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/leaderboard')
@login_required
def leaderboard():
    conn = get_db_connection()
    if not conn:
        return "Database error", 500
        
    cursor = conn.cursor(dictionary=True)
    
    leaderboard_query = """
        SELECT a.aid, a.title, s.username, 
               AVG(s.score) as avg_score,
               COUNT(DISTINCT s.tid) as tasks_completed,
               MAX(s.submit_at) as last_submission
        FROM submissions s
        JOIN assessments a ON s.aid = a.aid
        WHERE s.score = (
            SELECT MAX(score) 
            FROM submissions s2 
            WHERE s2.username = s.username AND s2.tid = s.tid
        )
        GROUP BY a.aid, s.username
        ORDER BY a.aid, avg_score DESC
    """
    cursor.execute(leaderboard_query)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    leaderboard_data = {}
    for row in results:
        if row['title'] not in leaderboard_data:
            leaderboard_data[row['title']] = []
        if len(leaderboard_data[row['title']]) < 5:
            leaderboard_data[row['title']].append(row)
    
    if not leaderboard_data:
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Leaderboard</title>
            {GLOBAL_CSS}
        </head>
        <body>
            <div class="container">
                <nav>
                    <a href="/home">🏠 Home</a>
                    <a href="/submit">📝 Submit SQL</a>
                    <a href="/submit_multiple">📚 Submit Multiple SQL</a>
                    <a href="/scores">📊 My Scores</a>
                    <a href="/leaderboard">🏆 Leaderboard</a>
                    <a href="/change_password">🔑 Change Password</a>
                    <a href="/export_csv">📥 Export CSV</a>
                    <a href="/admin/due_date">⚙️ Admin</a>
                    <a href="/login">🚪 Logout</a>
                </nav>
                <div class="content">
                    <h1>🏆 Leaderboard</h1>
                    <a href="/home">← Back to Home</a>
                    <p>No submissions yet. Be the first to appear on the leaderboard!</p>
                </div>
            </div>
        </body>
        </html>
        '''
    
    leaderboard_html = ''
    for title, entries in leaderboard_data.items():
        leaderboard_html += f'<h3>{title}</h3>'
        leaderboard_html += '<table class="score-table"><thead><tr><th>Rank</th><th>Student</th><th>Average Score</th><th>Tasks Completed</th></tr></thead><tbody>'
        for idx, entry in enumerate(entries, 1):
            medal = '🥇 ' if idx == 1 else ('🥈 ' if idx == 2 else ('🥉 ' if idx == 3 else f'#{idx} '))
            leaderboard_html += f'<tr><td>{medal}</td><td>{entry["username"]}</td><td>{entry["avg_score"]:.1f}/100</td><td>{entry["tasks_completed"]}</td></tr>'
        leaderboard_html += '</tbody></table><br>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Leaderboard - SQL Grader</title>
        {GLOBAL_CSS}
    </head>
    <body>
        <div class="container">
            <nav>
                <a href="/home">🏠 Home</a>
                <a href="/submit">📝 Submit SQL</a>
                <a href="/submit_multiple">📚 Submit Multiple SQL</a>
                <a href="/scores">📊 My Scores</a>
                <a href="/leaderboard">🏆 Leaderboard</a>
                <a href="/change_password">🔑 Change Password</a>
                <a href="/export_csv">📥 Export CSV</a>
                <a href="/admin/due_date">⚙️ Admin</a>
                <a href="/login">🚪 Logout</a>
            </nav>
            <div class="content">
                <h1>🏆 Leaderboard</h1>
                <a href="/home">← Back to Home</a>
                <p><small>Showing top 5 students per assessment based on average score</small></p>
                {leaderboard_html}
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/export_csv')
@login_required
def export_csv():
    conn = get_db_connection()
    if not conn:
        return "Database error", 500
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.username, a.title as assessment, t.title as task, 
               s.score, s.submit_at, s.attempt_number, s.feedback
        FROM submissions s
        JOIN assessments a ON s.aid = a.aid
        JOIN tasks t ON s.tid = t.tid
        WHERE s.username = %s
        ORDER BY s.submit_at DESC
    """, (session['username'],))
    
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Username', 'Assessment', 'Task', 'Score', 'Submission Date', 'Attempt Number', 'Feedback'])
    
    for row in data:
        submit_date = row['submit_at'].strftime('%Y-%m-%d %H:%M:%S') if row['submit_at'] else 'N/A'
        writer.writerow([
            row['username'],
            row['assessment'],
            row['task'],
            row['score'],
            submit_date,
            row['attempt_number'],
            row['feedback']
        ])
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment;filename=scores_{session['username']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )

@app.route('/admin/due_date', methods=['GET', 'POST'])
@login_required
def admin_due_date():
    if session['username'] not in ['test_student', 'admin']:
        flash('Admin access required', 'error')
        return redirect(url_for('home'))
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        aid = request.form['aid']
        new_due_date = request.form['due_date']
        
        cursor = conn.cursor()
        cursor.execute("UPDATE assessments SET due_date = %s WHERE aid = %s", (new_due_date, aid))
        conn.commit()
        cursor.close()
        
        flash(f'✅ Due date for assessment {aid} updated to {new_due_date}', 'success')
        return redirect(url_for('admin_due_date'))
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT aid, title, due_date FROM assessments ORDER BY aid")
    assessments = cursor.fetchall()
    cursor.close()
    conn.close()
    
    assessments_html = '<table class="score-table"><thead><tr><th>ID</th><th>Title</th><th>Current Due Date</th></tr></thead><tbody>'
    for a in assessments:
        assessments_html += f'<tr><td>{a["aid"]}</td><td>{a["title"]}</td><td>{a["due_date"]}</td></tr>'
    assessments_html += '</tbody></table>'
    
    messages = get_flashed_messages(with_categories=True)
    messages_html = ''
    for category, message in messages:
        messages_html += f'<div class="alert alert-{category}">{message}</div>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin - Update Due Dates</title>
        {GLOBAL_CSS}
    </head>
    <body>
        <div class="container">
            <nav>
                <a href="/home">🏠 Home</a>
                <a href="/submit">📝 Submit SQL</a>
                <a href="/submit_multiple">📚 Submit Multiple SQL</a>
                <a href="/scores">📊 My Scores</a>
                <a href="/leaderboard">🏆 Leaderboard</a>
                <a href="/change_password">🔑 Change Password</a>
                <a href="/export_csv">📥 Export CSV</a>
                <a href="/admin/due_date">⚙️ Admin</a>
                <a href="/login">🚪 Logout</a>
            </nav>
            <div class="content">
                <h1>⚙️ Admin - Update Due Dates</h1>
                <a href="/home">← Back to Home</a>
                {messages_html}
                
                <h3>Current Assessments</h3>
                {assessments_html}
                
                <h3>Update Due Date</h3>
                <form method="POST">
                    <div class="form-group">
                        <label>Assessment ID:</label>
                        <input type="text" name="aid" placeholder="e.g., 1" required>
                    </div>
                    <div class="form-group">
                        <label>New Due Date (YYYY-MM-DD HH:MM:SS):</label>
                        <input type="text" name="due_date" placeholder="2024-01-01 00:00:00" required>
                    </div>
                    <button type="submit">Update Due Date</button>
                </form>
                
                <div class="info-box">
                    <strong>📝 Demo Step 9 Instructions:</strong><br>
                    1. Change a due date to a past date (e.g., '2024-01-01 00:00:00')<br>
                    2. Re-run auto-grading or have students submit<br>
                    3. Observe the 10% late penalty applied to new submissions
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = hash_password(request.form['current_password'])
        new_password = hash_password(request.form['new_password'])
        confirm_password = hash_password(request.form['confirm_password'])
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return redirect(url_for('change_password'))
        
        conn = get_db_connection()
        if not conn:
            flash('Database error', 'error')
            return redirect(url_for('change_password'))
            
        cursor = conn.cursor()
        
        check_query = "SELECT * FROM students WHERE username = %s AND password_hash = %s"
        cursor.execute(check_query, (session['username'], current_password))
        
        if cursor.fetchone():
            update_query = "UPDATE students SET password_hash = %s WHERE username = %s"
            cursor.execute(update_query, (new_password, session['username']))
            conn.commit()
            flash('Password changed successfully!', 'success')
        else:
            flash('Current password is incorrect', 'error')
        
        cursor.close()
        conn.close()
        return redirect(url_for('change_password'))
    
    messages = get_flashed_messages(with_categories=True)
    messages_html = ''
    for category, message in messages:
        messages_html += f'<div class="alert alert-{category}">{message}</div>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Change Password - SQL Grader</title>
        {GLOBAL_CSS}
    </head>
    <body>
        <div class="container">
            <nav>
                <a href="/home">🏠 Home</a>
                <a href="/submit">📝 Submit SQL</a>
                <a href="/submit_multiple">📚 Submit Multiple SQL</a>
                <a href="/scores">📊 My Scores</a>
                <a href="/leaderboard">🏆 Leaderboard</a>
                <a href="/change_password">🔑 Change Password</a>
                <a href="/export_csv">📥 Export CSV</a>
                <a href="/admin/due_date">⚙️ Admin</a>
                <a href="/login">🚪 Logout</a>
            </nav>
            <div class="content">
                <h1>Change Password</h1>
                <a href="/home">← Back</a>
                {messages_html}
                <form method="POST">
                    <div class="form-group">
                        <label>Current Password:</label>
                        <input type="password" name="current_password" required>
                    </div>
                    <div class="form-group">
                        <label>New Password:</label>
                        <input type="password" name="new_password" required>
                    </div>
                    <div class="form-group">
                        <label>Confirm New Password:</label>
                        <input type="password" name="confirm_password" required>
                    </div>
                    <button type="submit">Change Password</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 SQL Assignment Grader - Full Version Starting...")
    print("=" * 60)
    print("📍 Open your browser and go to: http://127.0.0.1:5001")
    print("🔑 Login: test_student / password123")
    print()
    print("✅ All features implemented:")
    print("   • Login System with Hashed Passwords")
    print("   • Change Password")
    print("   • Single SQL Statement Submission")
    print("   • Multiple SQL Statements Submission")
    print("   • Auto-Grading Engine")
    print("   • Late Submission Penalty (10%)")
    print("   • Score Display with Visual Dashboard")
    print("   • Leaderboard (Top 5 per Assessment)")
    print("   • Re-submission Tracking")
    print("   • CSV Data Export")
    print("   • Admin Due Date Management")
    print("=" * 60)
    app.run(debug=True, host='127.0.0.1', port=5001)