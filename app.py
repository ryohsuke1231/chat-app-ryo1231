from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from email.message import EmailMessage
import sqlite3
import smtplib
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'

TOKEN_EXPIRATION_MINUTES = 10

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
            display_name TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS messages (
            name TEXT,
            text TEXT,
            time TEXT,
            read INTEGER
        )''')
init_db()

# メール送信
def send_login_email(email, token):
    from secrets__ import EMAIL_ADDRESS, EMAIL_PASSWORD
    login_link = f"https://chat-app-test-for-password.onrender.com/verify?token={token}"

    msg = EmailMessage()
    msg["Subject"] = "チャットログイン"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = email
    msg.set_content(f"ログインリンクはこちら:\n\n{login_link}", charset="utf-8")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

# ログイン画面
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        token = str(uuid.uuid4())
        expires_at = (datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRATION_MINUTES)).isoformat()

        with sqlite3.connect("chat.db") as conn:
            conn.execute("INSERT INTO tokens (email, token, expires_at) VALUES (?, ?, ?)",
                         (email, token, expires_at))

        send_login_email(email, token)
        return "確認リンクを送信しました！メールを確認してください。"

    return render_template('login.html')

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

# チャット画面
@app.route('/chat')
def chat():
    if 'user' not in session:
        return redirect(url_for('login'))

    email = session['user']
    with sqlite3.connect("users.db") as conn:
        cur = conn.execute("SELECT display_name FROM users WHERE email=?", (email,))
        row = cur.fetchone()

    display_name = row[0] if row else "Unknown"

    # ✅ メッセージを読み込む
    with sqlite3.connect("chat.db") as conn:
        cur = conn.execute("SELECT name, text, time, read FROM messages")
        rows = cur.fetchall()

    messages = [
        {"name": name, "text": text, "time": time, "read": read}
        for name, text, time, read in rows
    ]

    return render_template('chat.html', user=display_name, messages=messages, email=email)

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
