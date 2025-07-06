from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from email.message import EmailMessage
import sqlite3
import smtplib
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # セッション用

# トークンの有効期限（分）
TOKEN_EXPIRATION_MINUTES = 10

# SQLite 初期化（ユーザートークン＋メッセージ）
def init_db():
    with sqlite3.connect("chat.db") as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS tokens (
            email TEXT,
            token TEXT,
            expires_at TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS messages (
            name TEXT,
            text TEXT,
            time TEXT,
            read INTEGER
        )''')
init_db()

# メール送信（Gmail SMTP使用）
def send_login_email(email, token):
    from secrets import EMAIL_ADDRESS, EMAIL_PASSWORD
    login_link = f"https://chat-app-test-for-password.onrender.com/verify?token={token}"

    msg = EmailMessage()
    msg["Subject"] = "チャットログイン"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = email
    msg.set_content(f"ログインリンクはこちら:\n\n{login_link}", charset="utf-8")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
# ログインページ
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

# トークン認証
@app.route('/verify')
def verify():
    token = request.args.get('token')
    now = datetime.utcnow().isoformat()

    with sqlite3.connect("chat.db") as conn:
        cur = conn.execute("SELECT email FROM tokens WHERE token=? AND expires_at > ?", (token, now))
        row = cur.fetchone()

    if row:
        session['user'] = row[0]
        return redirect(url_for('chat'))
    else:
        return "このリンクは無効か、期限が切れています。"

@app.route('/chat')
def chat():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html', user=session['user'])

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# メッセージ送信
@app.route('/send', methods=['POST'])
def send_message():
    if 'user' not in session:
        return jsonify({"error": "未ログイン"}), 403

    data = request.get_json()
    now = datetime.now().strftime("%H:%M")
    name = session['user']
    text = data.get("text", "")

    with sqlite3.connect("chat.db") as conn:
        conn.execute("INSERT INTO messages (name, text, time, read) VALUES (?, ?, ?, ?)",
                     (name, text, now, 0))

    return jsonify({"status": "ok"})

# メッセージ読み込み
@app.route('/messages')
def get_messages():
    with sqlite3.connect("chat.db") as conn:
        cur = conn.execute("SELECT name, text, time, read FROM messages")
        rows = cur.fetchall()

    messages = [
        {"name": name, "text": text, "time": time, "read": read}
        for name, text, time, read in rows
    ]
    return jsonify(messages)

if __name__ == '__main__':
    app.run(debug=True)
