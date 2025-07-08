from flask import Flask, request, render_template, redirect, url_for, session, jsonify, send_from_directory

#from email.message import EmailMessage
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
#import smtplib
import uuid
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

TOKEN_EXPIRATION_MINUTES = 10

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#ICON_FOLDER = 'icons'
#os.makedirs(ICON_FOLDER, exist_ok=True)
#app.config['ICON_FOLDER'] = ICON_FOLDER

# SQLite 初期化（1つのDBに統合）
def init_db():
    with sqlite3.connect("chat.db") as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS tokens (
            email TEXT,
            token TEXT,
            expires_at TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            display_name TEXT,
            password TEXT,
            icon_filename TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS messages (
            name TEXT,
            text TEXT,
            time TEXT,
            read INTEGER,
            email TEXT
        )''')
init_db()

"""
# メール送信
def send_login_email(email, token):
    from secrets__ import EMAIL_ADDRESS, EMAIL_PASSWORD
    login_link = f"https://chat-app-by-ryosuke.onrender.com/verify?token={token}"

    msg = EmailMessage()
    msg["Subject"] = "チャットログイン"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = email
    msg.set_content(f"ログインリンクはこちら:\n\n{login_link}", charset="utf-8")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
"""

@app.route('/upload_icon', methods=['POST'])
def upload_icon():
    if 'user' not in session:
        return "Unauthorized", 403

    file = request.files.get('icon')
    if not file:
        return "No file", 400

    # ファイル名をユニーク化（例：メールアドレスのハッシュ + 拡張子）
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)

    email = session['user']
    with sqlite3.connect("chat.db") as conn:
        conn.execute("UPDATE users SET icon_filename=? WHERE email=?", (filename, email))

    return jsonify({"status": "ok", "filename": filename})


# ユーザー登録画面
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        display_name = request.form.get('display_name')
        icon_file = request.files.get('icon')

        # 必須チェック
        if not email or not password or not display_name or not icon_file:
            return "すべての項目（メール、名前、パスワード、アイコン画像）を入力してください。", 400

        # ファイルの保存
        ext = os.path.splitext(icon_file.filename)[1]
        filename = f"{uuid.uuid4().hex}{ext}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        icon_file.save(save_path)

        # パスワードハッシュ化
        hashed_password = generate_password_hash(password)

        with sqlite3.connect("chat.db") as conn:
            try:
                conn.execute("INSERT INTO users (email, display_name, password, icon_filename) VALUES (?, ?, ?, ?)",
                             (email, display_name, hashed_password, filename))
            except sqlite3.IntegrityError:
                return "このメールアドレスは既に登録されています。", 400

        session['user'] = email
        return redirect(url_for('chat'))

    return render_template('register.html')

# ログイン画面
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        with sqlite3.connect("chat.db") as conn:
            cur = conn.execute("SELECT password FROM users WHERE email=?", (email,))
            row = cur.fetchone()

        if row and check_password_hash(row[0], password):
            session['user'] = email
            return redirect(url_for('chat'))
        else:
            return "メールアドレスまたはパスワードが間違っています。"

    return render_template('login.html')

"""
# 認証
@app.route('/verify')
def verify():
    token = request.args.get('token')
    now = datetime.utcnow().isoformat()

    with sqlite3.connect("chat.db") as conn:
        cur = conn.execute("SELECT email FROM tokens WHERE token=? AND expires_at > ?", (token, now))
        row = cur.fetchone()

    if row:
        session['user'] = row[0]
        return redirect(url_for('name'))
    else:
        return "このリンクは無効か、期限が切れています。"
"""

"""
# 名前入力ページ
@app.route('/name', methods=['GET', 'POST'])
def name():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        display_name = request.form['display_name']
        email = session['user']

        with sqlite3.connect("chat.db") as conn:
            conn.execute('REPLACE INTO users (email, display_name) VALUES (?, ?)', (email, display_name))

        return redirect(url_for('chat'))

    return render_template('name.html')
"""

#ファイルのアップロード
@app.route('/upload', methods=['POST'])
def upload():
    if 'user' not in session:
        return "Unauthorized", 403

    file = request.files.get('file')
    if not file:
        return "No file", 400

    filename = file.filename
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)

    now = datetime.now().strftime("%H:%M")
    email = session['user']
    with sqlite3.connect("chat.db") as conn:
        cur = conn.execute("SELECT display_name FROM users WHERE email=?", (email,))
        row = cur.fetchone()
        name = row[0] if row else "Unknown"
        conn.execute("INSERT INTO messages (name, text, time, read, email) VALUES (?, ?, ?, ?, ?)",
                     (name, f"[ファイル] {filename}", now, 0, email))

    return "Uploaded", 200

@app.route('/files/<filename>')
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# チャット画面
@app.route('/chat')
def chat():
    if 'user' not in session:
        return redirect(url_for('login'))

    email = session['user']
    with sqlite3.connect("chat.db") as conn:
        # 表示名の取得
        cur = conn.execute("SELECT display_name FROM users WHERE email=?", (email,))
        rows = cur.fetchall()
        display_name = rows[0][0] if rows else "Unknown"

        # メッセージ取得
        cur = conn.execute("SELECT name, text, time, read, email FROM messages")
        messages = [
            {"name": name, "text": text, "time": time, "read": read, "email": email}
            for name, text, time, read, email in cur.fetchall()
        ]

        # ✅ メンバー一覧取得
        cur = conn.execute("SELECT display_name FROM users")
        members = [row[0] for row in cur.fetchall()]

    return render_template('chat.html', user=display_name, messages=messages, email=email, members=members)

# メッセージ送信
@app.route('/send', methods=['POST'])
def send_message():
    if 'user' not in session:
        return jsonify({"error": "未ログイン"}), 403

    data = request.get_json()
    now = datetime.now().strftime("%H:%M")

    email = session['user']
    with sqlite3.connect("chat.db") as conn:
        cur = conn.execute("SELECT display_name FROM users WHERE email=?", (email,))
        row = cur.fetchone()

    name = row[0] if row else "Unknown"
    text = data.get("text", "")

    with sqlite3.connect("chat.db") as conn:
        #conn.execute("ALTER TABLE messages ADD COLUMN email TEXT")  # 初回だけ実行すればOK
        conn.execute("INSERT INTO messages (name, text, time, read, email) VALUES (?, ?, ?, ?, ?)",
                     (name, text, now, 0, email))

    return jsonify({"status": "ok"})

#メッセージ読み込み
@app.route('/messages')
def get_messages():
    with sqlite3.connect("chat.db") as conn:
        cur = conn.execute("SELECT name, text, time, read, email FROM messages")
        rows = cur.fetchall()

    messages = [
        {"name": name, "text": text, "time": time, "read": read, "email": email}
        for name, text, time, read, email in rows
    ]

    return jsonify(messages)


# ログアウト
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
