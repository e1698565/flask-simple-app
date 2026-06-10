from flask import Flask, request, redirect, url_for, session, flash, get_flashed_messages
from functools import wraps
import hashlib
import secrets
import mysql.connector
from mysql.connector import Error

# Database configuration (using a new database 'simple_app')
DB_CONFIG = {
    'host': 'localhost',
    'database': 'simple_app',
    'user': 'root',
    'password': 'root',   # Change to your MariaDB root password
    'port': 3306
}

def get_db_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        print(f"DB error: {e}")
        return None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ---------- Routes ----------
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
        cursor.execute("SELECT * FROM users WHERE username = %s AND password_hash = %s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            session['username'] = username
            flash('Login successful', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Login - Simple DB App</title></head>
    <body>
        <h1>Simple Database App</h1>
        <h2>Login</h2>
        ''' + ''.join([f'<p style="color:red">{msg}</p>' for msg in get_flashed_messages()]) + '''
        <form method="post">
            <label>Username:</label> <input type="text" name="username" required><br><br>
            <label>Password:</label> <input type="password" name="password" required><br><br>
            <button type="submit">Login</button>
        </form>
        <hr>
        <h3>Test credentials</h3>
        <p>Username: <code>admin</code><br>Password: <code>admin123</code></p>
        <p><i>First-time setup: The database and user table will be created automatically when you run this app.</i></p>
    </body>
    </html>
    '''

@app.route('/dashboard')
@login_required
def dashboard():
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Dashboard</title></head>
    <body>
        <h1>Welcome, {session['username']}!</h1>
        <hr>
        <h2>Operations</h2>
        <ul>
            <li><a href="/create_table">Create table "people"</a></li>
            <li><a href="/table_structure">View table structure</a></li>   <!-- NEW OPTION -->
            <li><a href="/insert">Insert a name</a></li>
            <li><a href="/list">List all names</a></li>
            <li><a href="/delete">Delete a name (by id)</a></li>
            <li><a href="/drop_table">Drop table "people"</a></li>
            <li><a href="/logout">Logout</a></li>
        </ul>
        <hr>
        <p><i>Note: After dropping the table, you must re-create it before inserting data.</i></p>
    </body>
    </html>
    '''

@app.route('/create_table')
@login_required
def create_table():
    conn = get_db_connection()
    if not conn:
        flash('DB connection error', 'error')
        return redirect(url_for('dashboard'))
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS people (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        flash('Table "people" created successfully (or already exists).', 'success')
    except Error as e:
        flash(f'Error: {e}', 'error')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('dashboard'))

# ---------- NEW ROUTE: View table structure ----------
@app.route('/table_structure')
@login_required
def table_structure():
    conn = get_db_connection()
    if not conn:
        flash('DB connection error', 'error')
        return redirect(url_for('dashboard'))
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("DESCRIBE people")
        columns = cursor.fetchall()
        if not columns:
            flash('Table "people" does not exist. Please create it first.', 'error')
            return redirect(url_for('dashboard'))
        # Build HTML table for structure
        html = '''
        <!DOCTYPE html>
        <html>
        <head><title>Table Structure</title></head>
        <body>
            <h1>Structure of table "people"</h1>
            <table border="1">
                <tr><th>Field</th><th>Type</th><th>Null</th><th>Key</th><th>Default</th><th>Extra</th></tr>
        '''
        for col in columns:
            html += f'''
                <tr>
                    <td>{col['Field']}</td>
                    <td>{col['Type']}</td>
                    <td>{col['Null']}</td>
                    <td>{col['Key']}</td>
                    <td>{col['Default']}</td>
                    <td>{col['Extra']}</td>
                </tr>
            '''
        html += '''
            </table>
            <p><a href="/dashboard">Back to Dashboard</a></p>
        </body>
        </html>
        '''
        return html
    except Error as e:
        flash(f'Error: {e}. Maybe the table does not exist.', 'error')
        return redirect(url_for('dashboard'))
    finally:
        cursor.close()
        conn.close()

@app.route('/insert', methods=['GET', 'POST'])
@login_required
def insert():
    if request.method == 'POST':
        name = request.form['name'].strip()
        if not name:
            flash('Name cannot be empty', 'error')
            return redirect(url_for('insert'))
        conn = get_db_connection()
        if not conn:
            flash('DB error', 'error')
            return redirect(url_for('dashboard'))
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO people (name) VALUES (%s)", (name,))
            conn.commit()
            flash(f'Inserted: {name}', 'success')
        except Error as e:
            flash(f'Insert failed: {e}. Did you create the table?', 'error')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('list'))
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Insert Name</title></head>
    <body>
        <h1>Insert a new name</h1>
        ''' + ''.join([f'<p style="color:red">{msg}</p>' for msg in get_flashed_messages()]) + '''
        <form method="post">
            <label>Name:</label> <input type="text" name="name" required><br><br>
            <button type="submit">Insert</button>
        </form>
        <p><a href="/dashboard">Back to Dashboard</a></p>
    </body>
    </html>
    '''

@app.route('/list')
@login_required
def list_names():
    conn = get_db_connection()
    if not conn:
        flash('DB error', 'error')
        return redirect(url_for('dashboard'))
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, name, created_at FROM people ORDER BY id")
        rows = cursor.fetchall()
    except Error:
        flash('Table "people" does not exist. Please create it first.', 'error')
        rows = []
    cursor.close()
    conn.close()

    if not rows:
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>List Names</title></head>
        <body>
            <h1>List of names</h1>
            <p>No records found. <a href="/create_table">Create table</a> and then <a href="/insert">insert</a> some names.</p>
            <p><a href="/dashboard">Back</a></p>
        </body>
        </html>
        '''
    html = '<h1>People List</h1><table border="1"><tr><th>ID</th><th>Name</th><th>Created At</th></tr>'
    for r in rows:
        html += f'<tr><td>{r["id"]}</td><td>{r["name"]}</td><td>{r["created_at"]}</td></tr>'
    html += '</table><p><a href="/dashboard">Back to Dashboard</a></p>'
    return html

@app.route('/delete', methods=['GET', 'POST'])
@login_required
def delete():
    if request.method == 'POST':
        record_id = request.form['id']
        if not record_id.isdigit():
            flash('Invalid ID', 'error')
            return redirect(url_for('delete'))
        conn = get_db_connection()
        if not conn:
            flash('DB error', 'error')
            return redirect(url_for('dashboard'))
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM people WHERE id = %s", (record_id,))
            conn.commit()
            if cursor.rowcount > 0:
                flash(f'Deleted record with id {record_id}', 'success')
            else:
                flash(f'ID {record_id} not found', 'error')
        except Error as e:
            flash(f'Delete failed: {e}', 'error')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('list'))
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Delete by ID</title></head>
    <body>
        <h1>Delete a record by ID</h1>
        ''' + ''.join([f'<p style="color:red">{msg}</p>' for msg in get_flashed_messages()]) + '''
        <form method="post">
            <label>ID to delete:</label> <input type="number" name="id" required><br><br>
            <button type="submit">Delete</button>
        </form>
        <p><a href="/dashboard">Back</a></p>
    </body>
    </html>
    '''

@app.route('/drop_table')
@login_required
def drop_table():
    conn = get_db_connection()
    if not conn:
        flash('DB error', 'error')
        return redirect(url_for('dashboard'))
    cursor = conn.cursor()
    try:
        cursor.execute("DROP TABLE IF EXISTS people")
        conn.commit()
        flash('Table "people" dropped successfully.', 'success')
    except Error as e:
        flash(f'Error: {e}', 'error')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'success')
    return redirect(url_for('login'))

# ---------- Initialize database and default user on first run ----------
def init_db():
    conn = get_db_connection()
    if not conn:
        print("❌ Could not connect to MariaDB. Make sure it's running (mysqld_safe &).")
        return
    cursor = conn.cursor()
    try:
        # Create database if not exists
        cursor.execute("CREATE DATABASE IF NOT EXISTS simple_app")
        cursor.execute("USE simple_app")
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(50) PRIMARY KEY,
                password_hash VARCHAR(255) NOT NULL
            )
        ''')
        # Insert default admin user (admin / admin123)
        admin_pass = hash_password('admin123')
        cursor.execute("INSERT IGNORE INTO users (username, password_hash) VALUES (%s, %s)", ('admin', admin_pass))
        conn.commit()
        print("✅ Database 'simple_app' and user table ready.")
        print("   Default login: admin / admin123")
    except Error as e:
        print(f"Init error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    init_db()
    print("="*50)
    print("🚀 Simple DB App starting...")
    print("📍 http://127.0.0.1:5002")
    print("🔑 Login: admin / admin123")
    print("="*50)
    app.run(debug=True, host='127.0.0.1', port=5002)