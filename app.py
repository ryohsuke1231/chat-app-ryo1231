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

ICON_FOLDER = 'icons'
os.makedirs(ICON_FOLDER, exist_ok=True)
app.config['ICON_FOLDER'] = ICON_FOLDER

#@app.before_request
#def log_request():
    #print(f"[リクエスト] {request.method} {request.path}")


# SQLite 初期化（1つのDBに統合）
def init_db():
    with sqlite3.connect("chat.db") as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS tokens (
            email TEXT,
            token TEXT,
            expires_at TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            display_name TEXT,
            password TEXT,
            icon_is_default INTEGER DEFAULT 1,
            icon_filename TEXT DEFAULT NULL
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    save_path = os.path.join(app.config['ICON_FOLDER'], filename)
    file.save(save_path)
    #filename += '/icons/'

    email = session['user']
    with sqlite3.connect("chat.db") as conn:
        conn.execute("UPDATE users SET icon_filename=?, icon_is_default=0 WHERE email=?", (filename, email))

    return jsonify({"status": "ok", "filename": filename})


# ユーザー登録画面
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        display_name = request.form.get('display_name')
        icon = request.files.get('icon')

        if not email or not password or not display_name:
            return render_template('register.html', error="すべての項目を入力してください。")

        if password != confirm_password:
            return render_template('register.html', error="パスワードが一致しません。")

        if not icon:
            filename = ""
        else:
            ext = os.path.splitext(icon.filename)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(app.config['ICON_FOLDER'], filename)
            icon.save(save_path)

        hashed_password = generate_password_hash(password)

        with sqlite3.connect("chat.db") as conn:
            try:
                conn.execute("INSERT INTO users (email, display_name, password, icon_filename, icon_is_default) VALUES (?, ?, ?, ?, ?)",
                             (email, display_name, hashed_password, filename, 0))
            except sqlite3.IntegrityError:
                return render_template('register.html', error="このメールアドレスは既に登録されています。")

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
            cur = conn.execute("SELECT id, password FROM users WHERE email=?", (email,))
            row = cur.fetchone()

        if row and check_password_hash(row[1], password):
            session['user'] = email
            session['uid'] = row[0]  # ← ここを追加！
            return redirect(url_for('chat'))
        else:
            #return render_template('login_failed.html')
            return render_template('login.html', error="メールアドレスまたはパスワードが間違っています。")

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
    #id = str(uuid.uuid4())
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
        # ユーザー情報（表示名＋アイコン）を取得
        cur = conn.execute("SELECT display_name, icon_filename, icon_is_default FROM users WHERE email=?", (email,))
        row = cur.fetchone()
        display_name = row[0] if row else "Unknown"
        user_icon = row[1] if row and row[1] else None
        user_icon_is_default = row[2] if row else 1

        # 全ユーザーの名前とアイコンを取得（メンバーリスト用）
        cur = conn.execute("SELECT display_name, icon_filename, icon_is_default FROM users")
        members = [{"name": r[0], "icon": r[1], "icon_is_default": r[2]} for r in cur.fetchall()]

        # メッセージ取得（名前だけでなく送信者のアイコンも含める場合はクエリ変更が必要）
        cur = conn.execute("SELECT id, name, text, time, read, email FROM messages")
        messages = []
        for id, name, text, time_, read, email_ in cur.fetchall():
            # 送信者のアイコン取得
            cur_icon = conn.execute("SELECT icon_filename, icon_is_default FROM users WHERE email=?", (email_,))
            icon_row = cur_icon.fetchone()
            icon = icon_row[0] if icon_row and icon_row[0] else None
            messages.append({
                "id": id,
                "name": name,
                "text": text,
                "time": time_,
                "read": read,
                "email": email_,
                "icon": icon,
                "icon_is_default": icon_row[1] if icon_row else 1
            })
            print(f"Message from {name}: {text} at {time_}, read: {read}, email: {email_}, icon: {icon}, icon_is_default: {icon_row[1] if icon_row else 1}")

    return render_template('chat.html', user=display_name, user_icon=user_icon, user_icon_is_default=user_icon_is_default, messages=messages, email=email, members=members)

#アイコン取得
@app.route('/icons/<filename>')
def serve_icon(filename):
    return send_from_directory(app.config['ICON_FOLDER'], filename)

@app.route('/api/update-profile', methods=['POST'])
def update_profile():
    print("¥n¥n¥n¥nUpdating profile...")
    uid = session.get("uid")
    if not uid:
        print("¥nUser not logged in")
        return jsonify({"success": False, "error": "ログインしていません"}), 401

    name = request.form.get("name")  # ← JSONではなくformから取得
    icon = request.files.get("icon")
    print(f"Updating profile for UID {uid}: name={name}, icon={icon}")

    with sqlite3.connect("chat.db") as db:
        if icon:
            ext = os.path.splitext(icon.filename)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(app.config['ICON_FOLDER'], filename)
            icon.save(save_path)
            db.execute("UPDATE users SET display_name=?, icon_filename=? WHERE id=?", (name, filename, uid))
            print(f"uid={uid}のユーザーのアイコン、名前を更新しました: {filename}, {name}")
        else:
            db.execute("UPDATE users SET display_name=? WHERE id=?", (name, uid))
            print(f"uid={uid}のユーザーの名前を更新しました: {name}")

    #session.clear()
    session['name'] = name  # セッションに名前を保存
    session['icon'] = filename if icon else session.get('icon', None)  # アイコンがない場合は既存のアイコンを保持
    #return redirect('/login')
    return jsonify({"success": True})

# メッセージ送信
@app.route('/send', methods=['POST'])
def send_message():
    print("sending message...")
    if 'user' not in session:
        print("User not logged in")
        return jsonify({"error": "未ログイン"}), 403

    data = request.get_json()
    now = datetime.now().strftime("%H:%M")

    email = session['user']
    with sqlite3.connect("chat.db") as conn:
        cur = conn.execute("SELECT display_name FROM users WHERE email=?", (email,))
        row = cur.fetchone()

    name = row[0] if row else "Unknown"
    text = data.get("text", "")
    #random_id = str(uuid.uuid4())

    with sqlite3.connect("chat.db") as conn:
        #conn.execute("ALTER TABLE messages ADD COLUMN email TEXT")  # 初回だけ実行すればOK
        conn.execute("INSERT INTO messages (name, text, time, read, email) VALUES (?, ?, ?, ?, ?)",
                     (name, text, now, 0, email))

    print(f"Message sent successfully by {name}: {text} at {now}, email: {email}")
    return jsonify({"status": "ok"})

#メッセージ読み込み
@app.route('/messages')
def get_messages():
    with sqlite3.connect("chat.db") as conn:
        cur = conn.execute("SELECT id, name, text, time, read, email FROM messages")
        rows = cur.fetchall()

        messages = []
        for id, name, text, time_, read, email in rows:
            cur_icon = conn.execute("SELECT icon_filename, icon_is_default FROM users WHERE email=?", (email,))
            icon_row = cur_icon.fetchone()
            icon = icon_row[0] if icon_row and icon_row[0] else None
            messages.append({
                "id": id,
                "name": name,
                "text": text,
                "time": time_,
                "read": read,
                "email": email,
                "icon": icon,
                "icon_is_default": icon_row[1] if icon_row else 1
            })

    return jsonify(messages)

# ログアウト
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route("/api/user-info")
def user_info():
    uid = session.get("uid")
    if not uid:
        return jsonify({"error": "未ログイン"}), 401

    with sqlite3.connect("chat.db") as db:
        db.row_factory = sqlite3.Row
        user = db.execute("SELECT display_name, icon_filename, icon_is_default, email FROM users WHERE id = ?", (uid,)).fetchone()
        if not user:
            return jsonify({"error": "ユーザーが見つかりません"}), 404

        return jsonify({
            "name": user["display_name"],
            "iconUrl": (
                "/static/default.jpeg"
                if user["icon_is_default"]
                else f"/icons/{user['icon_filename']}"
            ),    
            "email": user["email"],
            "icon_is_default": user["icon_is_default"]
        })

@app.route("/send_debug", methods=["POST"])
def receive_message():
    data = request.get_json()
    text = data.get("text")

    print(f"[受信メッセージ] {text}")  # ← ターミナルに出る
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(debug=True)
