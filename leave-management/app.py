from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import date
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = 'leave_mgmt_secret_2024'

# ─── MySQL Configuration ───────────────────────────────────────────────────
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'          # Change to your MySQL username
app.config['MYSQL_PASSWORD'] = 'yvsg2003'          # Change to your MySQL password
app.config['MYSQL_DB'] = 'leave_management'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

# ─── Email Config (optional) ───────────────────────────────────────────────
EMAIL_SENDER = 'youremail@gmail.com'       # Your Gmail
EMAIL_PASSWORD = 'your_app_password'       # Gmail App Password
EMAIL_ENABLED = False                      # Set True to enable emails


# ─── Helpers ──────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def manager_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'manager':
            flash('Access denied. Managers only.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def send_email(to_email, subject, body):
    if not EMAIL_ENABLED:
        return
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_SENDER
        msg['To'] = to_email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"Email error: {e}")

def count_days(from_date, to_date):
    delta = to_date - from_date
    return delta.days + 1


# ─── Routes ───────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        department = request.form['department']

        hashed_pw = generate_password_hash(password)
        cur = mysql.connection.cursor()

        cur.execute("SELECT id FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))

        cur.execute(
            "INSERT INTO users (name, email, password, role, department) VALUES (%s,%s,%s,%s,%s)",
            (name, email, hashed_pw, role, department)
        )
        mysql.connection.commit()
        user_id = cur.lastrowid

        cur.execute(
            "INSERT INTO leave_balance (user_id, total_leaves, used_leaves, remaining_leaves) VALUES (%s, 20, 0, 20)",
            (user_id,)
        )
        mysql.connection.commit()
        cur.close()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['role'] = user['role']
            session['email'] = user['email']
            flash(f"Welcome back, {user['name']}!", 'success')
            if user['role'] == 'manager':
                return redirect(url_for('manager_dashboard'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))


# ─── Employee Routes ───────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM leave_balance WHERE user_id=%s", (session['user_id'],))
    balance = cur.fetchone()

    cur.execute(
        "SELECT * FROM leaves WHERE user_id=%s ORDER BY applied_on DESC",
        (session['user_id'],)
    )
    leaves = cur.fetchall()
    cur.close()
    return render_template('dashboard.html', balance=balance, leaves=leaves)


@app.route('/apply', methods=['GET', 'POST'])
@login_required
def apply_leave():
    if session.get('role') == 'manager':
        flash('Managers cannot apply for leave from this page.', 'warning')
        return redirect(url_for('manager_dashboard'))

    if request.method == 'POST':
        leave_type = request.form['leave_type']
        from_date = request.form['from_date']
        to_date = request.form['to_date']
        reason = request.form['reason']

        from_d = date.fromisoformat(from_date)
        to_d = date.fromisoformat(to_date)

        if to_d < from_d:
            flash('End date cannot be before start date.', 'danger')
            return redirect(url_for('apply_leave'))

        days = count_days(from_d, to_d)

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM leave_balance WHERE user_id=%s", (session['user_id'],))
        balance = cur.fetchone()

        if days > balance['remaining_leaves']:
            flash(f'Not enough leave balance. You have {balance["remaining_leaves"]} days left.', 'danger')
            cur.close()
            return redirect(url_for('apply_leave'))

        cur.execute(
            "INSERT INTO leaves (user_id, leave_type, from_date, to_date, reason) VALUES (%s,%s,%s,%s,%s)",
            (session['user_id'], leave_type, from_date, to_date, reason)
        )
        mysql.connection.commit()
        cur.close()

        flash(f'Leave applied successfully for {days} day(s). Waiting for approval.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('apply_leave.html')


# ─── Manager Routes ────────────────────────────────────────────────────────

@app.route('/manager/dashboard')
@manager_required
def manager_dashboard():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT l.*, u.name as emp_name, u.email as emp_email, u.department
        FROM leaves l
        JOIN users u ON l.user_id = u.id
        ORDER BY 
            CASE l.status WHEN 'Pending' THEN 0 ELSE 1 END,
            l.applied_on DESC
    """)
    leaves = cur.fetchall()

    cur.execute("SELECT COUNT(*) as total FROM leaves WHERE status='Pending'")
    pending_count = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) as total FROM users WHERE role='employee'")
    emp_count = cur.fetchone()['total']
    cur.close()

    return render_template('manager_dashboard.html', leaves=leaves,
                           pending_count=pending_count, emp_count=emp_count)


@app.route('/manager/action/<int:leave_id>/<action>', methods=['POST'])
@manager_required
def leave_action(leave_id, action):
    comment = request.form.get('comment', '')
    status = 'Approved' if action == 'approve' else 'Rejected'

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM leaves WHERE id=%s", (leave_id,))
    leave = cur.fetchone()

    if not leave:
        flash('Leave record not found.', 'danger')
        cur.close()
        return redirect(url_for('manager_dashboard'))

    cur.execute(
        "UPDATE leaves SET status=%s, manager_comment=%s WHERE id=%s",
        (status, comment, leave_id)
    )

    if status == 'Approved':
        days = count_days(leave['from_date'], leave['to_date'])
        cur.execute("""
            UPDATE leave_balance
            SET used_leaves = used_leaves + %s,
                remaining_leaves = remaining_leaves - %s
            WHERE user_id = %s
        """, (days, days, leave['user_id']))

    mysql.connection.commit()

    cur.execute("SELECT email, name FROM users WHERE id=%s", (leave['user_id'],))
    emp = cur.fetchone()
    cur.close()

    send_email(
        emp['email'],
        f"Leave {status} - Leave Management System",
        f"Dear {emp['name']},\n\nYour leave request from {leave['from_date']} to {leave['to_date']} has been {status}.\n\nManager Comment: {comment or 'No comment'}\n\nRegards,\nHR Team"
    )

    flash(f"Leave {status} successfully!", 'success')
    return redirect(url_for('manager_dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
