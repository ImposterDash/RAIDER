from flask import Flask, request, render_template_string, redirect, url_for
import threading
import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head><title>SecureCorp Login</title></head>
<body style="font-family: sans-serif; text-align: center; padding-top: 50px; background-color: #f4f4f4;">
    <div style="background: white; width: 300px; margin: auto; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
        <h2>SecureCorp Bank</h2>
        <form action="/login" method="POST">
            <input type="text" name="username" placeholder="Username" style="width: 90%; padding: 8px; margin: 5px;"><br>
            <input type="password" name="password" placeholder="Password" style="width: 90%; padding: 8px; margin: 5px;"><br>
            <button type="submit" style="width: 100%; padding: 10px; background: #007bff; color: white; border: none; cursor: pointer;">Login</button>
        </form>
        <p style="color: red;">{{ error }}</p>
        <br>
        <a href="/feedback" style="color: #666; font-size: 0.9em;">Leave Feedback</a>
    </div>
</body>
</html>
"""

DASHBOARD_PAGE = """
<!DOCTYPE html>
<html>
<head><title>Admin Dashboard</title></head>
<body style="font-family: sans-serif; text-align: center; padding-top: 50px; background-color: #e0ffe0;">
    <div style="background: white; width: 400px; margin: auto; padding: 20px; border-radius: 8px; border: 2px solid green;">
        <h1 style="color: green;">ACCESS GRANTED</h1>
        <p>Welcome, Administrator.</p>
        <hr>
        <p><strong>Confidential Flag:</strong> <span style="font-family: monospace; background: #eee; padding: 5px;">FLAG{MULTI_AGENT_DOMINATION}</span></p>
        <br>
        <button onclick="window.location.href='/'">Logout</button>
    </div>
</body>
</html>
"""

SQL_ERROR_PAGE = """
<html><body>
<h1>Database Error</h1>
<p>You have an error in your SQL syntax; check the manual that corresponds to your MySQL server version for the right syntax to use near '' AND password=''' at line 1.</p>
</body></html>
"""

FEEDBACK_PAGE = """
<!DOCTYPE html>
<html>
<head><title>SecureCorp Feedback</title></head>
<body style="font-family: sans-serif; text-align: center; padding-top: 50px; background-color: #fff8e1;">
    <div style="background: white; width: 400px; margin: auto; padding: 20px; border-radius: 8px; border: 1px solid #ffe0b2;">
        <h2>Customer Feedback</h2>
        <p>We value your opinion!</p>
        <form action="/feedback" method="GET">
            <input type="text" name="msg" placeholder="Your message..." style="width: 80%; padding: 8px;">
            <button type="submit">Submit</button>
        </form>
        <br>
        <div style="text-align: left; padding: 10px; background: #f9f9f9; border: 1px solid #eee;">
            <strong>Recent Feedback:</strong><br>
            <!-- VULNERABILITY: Input is reflected without sanitization -->
            <span>REPLACE_FEEDBACK</span>
        </div>
        <br>
        <a href="/">Back to Login</a>
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def home():
    return render_template_string(LOGIN_PAGE)

@app.route('/login', methods=['POST'])
def login():
    user = request.form.get('username', '')
    
    if user == "'":
        return render_template_string(SQL_ERROR_PAGE), 500
        
    if "' OR 1=1" in user.upper() or '" OR 1=1' in user.upper() or "ADMIN' --" in user.upper():
        return redirect(url_for('dashboard'))
        
    return render_template_string(LOGIN_PAGE, error="Invalid Credentials")

@app.route('/dashboard')
def dashboard():
    return render_template_string(DASHBOARD_PAGE)

@app.route('/feedback', methods=['GET'])
def feedback():
    msg = request.args.get('msg', '')
    return render_template_string(FEEDBACK_PAGE.replace('REPLACE_FEEDBACK', msg))

def run_server():
    app.run(port=5000)

if __name__ == "__main__":
    run_server()