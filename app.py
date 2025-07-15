from flask import (
    Flask, request, render_template, redirect,
    url_for, session, jsonify, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import uuid
from datetime import datetime, timezone
import os
#/from dotenv import load_dotenv
import logging
logging.getLogger('werkzeug').setLevel(logging.DEBUG)


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# === 設定 ===
UPLOAD_FOLDER = 'uploads'
ICON_FOLDER = 'icons'
TOKEN_EXPIRATION_MINUTES = 10
APP_PASSWORD = 'hellodrone1231@yeah@gakuho_1B.students'  # アプリアクセス用パスワード
#load_dotenv()
#APP_PASSWORD = os.getenv('APP_PASSWORD')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ICON_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ICON_FOLDER'] = ICON_FOLDER

# === データベース初期化 ===
def init_db():
    with sqlite3.connect("chat.db") as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tokens (
                email TEXT,
                token TEXT,
                expires_at TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                display_name TEXT,
                password TEXT,
                icon_is_default INTEGER DEFAULT 1,
                icon_filename TEXT DEFAULT NULL,
                last_comment_time INTEGER DEFAULT -1
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                text TEXT,
                time TEXT,
                read INTEGER,
                email TEXT
            )
        ''')
init_db()

# === アプリパスワード認証 ===
@app.route('/app_auth', methods=['GET', 'POST'])
def app_auth():
    # 既に認証済みの場合はログイン画面へリダイレクト
    if session.get('app_authenticated', False):
        print("既にアプリパスワード認証済みです。ログイン画面へリダイレクト")
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        app_password = str(request.form.get('app_password'))
        if app_password == APP_PASSWORD:
            print("アプリパスワード認証成功")
            session['app_authenticated'] = True
            session.permanent = True  # セッションを永続化
            return redirect(url_for('login'))
        else:
            print("アプリパスワード認証失敗")
            return render_template('app_password.html', error="アプリパスワードが間違っています。")
    return render_template('app_password.html')

# アプリ認証チェック関数
def check_app_auth():
    return session.get('app_authenticated', False)

# === ユーザー登録 ===
@app.route('/register', methods=['GET', 'POST'])
def register():
    # アプリパスワード認証チェック
    if not check_app_auth():
        return redirect(url_for('app_auth'))
        
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

        filename = ""
        if icon:
            ext = os.path.splitext(str(icon.filename))[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            icon.save(os.path.join(app.config['ICON_FOLDER'], filename))

        hashed_password = generate_password_hash(password)
        try:
            with sqlite3.connect("chat.db") as conn:
                conn.execute('''
                    INSERT INTO users (email, display_name, password, icon_filename, icon_is_default)
                    VALUES (?, ?, ?, ?, ?)
                ''', (email, display_name, hashed_password, filename, 0 if icon else 1))
        except sqlite3.IntegrityError:
            return render_template('register.html', error="このメールアドレスは既に登録されています。")

        session['user'] = email
        return redirect(url_for('login'))
    return render_template('register.html')


# === ログイン ===
@app.route('/', methods=['GET', 'POST'])
def login():
    # アプリパスワード認証チェック
    if not check_app_auth():
        return redirect(url_for('app_auth'))
        
    if request.method == 'POST':
        email = str(request.form.get('email'))
        password = str(request.form.get('password'))

        with sqlite3.connect("chat.db") as conn:
            cur = conn.execute("SELECT id, password FROM users WHERE email=?", (email,))
            row = cur.fetchone()

        if row and check_password_hash(row[1], password):
            session['user'] = email
            session['uid'] = row[0]
            return redirect(url_for('chat'))

        return render_template('login.html', error="メールアドレスまたはパスワードが間違っています。")

    return render_template('login.html')


# === アイコンアップロード（ログイン中） ===
@app.route('/upload_icon', methods=['POST'])
def upload_icon():
    if 'user' not in session:
        return "Unauthorized", 403

    file = request.files.get('icon')
    if not file:
        return "No file", 400

    ext = os.path.splitext(str(file.filename))[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    file.save(os.path.join(app.config['ICON_FOLDER'], filename))

    email = session['user']
    with sqlite3.connect("chat.db") as conn:
        conn.execute("UPDATE users SET icon_filename=?, icon_is_default=0 WHERE email=?", (filename, email))

    return jsonify({"status": "ok", "filename": filename})


#ファイルのアップロード
@app.route('/upload', methods=['POST'])
def upload():
    if 'user' not in session:
        return "Unauthorized", 403

    file = request.files.get('file')
    if not file:
        return "No file", 400

    filename = file.filename
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], str(filename))
    file.save(save_path)
    #id = str(uuid.uuid4())
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    now_sec = int(datetime.now(timezone.utc).timestamp())
    email = session['user']
    with sqlite3.connect("chat.db") as conn:
        cur = conn.execute("SELECT display_name FROM users WHERE email=?", (email,))
        row = cur.fetchone()
        name = row[0] if row else "Unknown"
        conn.execute("INSERT INTO messages (name, text, time, read, email) VALUES (?, ?, ?, ?, ?)",
                     (name, f"[ファイル] {filename}", now, 0, email))
        conn.execute('''
        UPDATE users SET last_comment_time = ? WHERE email = ?''', (now_sec, email))

    return "Uploaded", 200

@app.route('/files/<filename>')
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# チャット画面
@app.route('/chat')
def chat():
    # アプリパスワード認証チェック
    if not check_app_auth():
        return redirect(url_for('app_auth'))
        
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
            #print(f"Message from {name}: {text} at {time_}, read: {read}, email: {email_}, icon: {icon}, icon_is_default: {icon_row[1] if icon_row else 1}")

    return render_template('chat.html', user=display_name, user_icon=user_icon, user_icon_is_default=user_icon_is_default, messages=messages, email=email, members=members)

#アイコン取得
@app.route('/icons/<filename>')
def serve_icon(filename):
    return send_from_directory(app.config['ICON_FOLDER'], str(filename))

@app.route('/api/update-profile', methods=['POST'])
def update_profile():
    if 'user' not in session:
        print("Unauthorized access to update profile")
        return "Unauthorized", 403
    print("Updating profile...")

    email = session['user']
    new_name = request.form.get('name')
    icon = request.files.get('icon')
    print(f"New name: {new_name}, New icon: {icon.filename if icon else 'None'}")
    print("updating database...")

    with sqlite3.connect("chat.db") as conn:
        # 旧ユーザー情報を取得（古いアイコン削除のため）
        cur = conn.execute("SELECT icon_filename, icon_is_default FROM users WHERE email=?", (email,))
        row = cur.fetchone()
        old_icon_filename = row[0]
        old_icon_is_default = row[1]

        # 更新内容の組み立て
        update_fields = []
        update_values = []

        if new_name:
            update_fields.append("display_name=?")
            update_values.append(new_name)

        if icon and icon.filename:
            ext = os.path.splitext(secure_filename(icon.filename))[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(app.config['ICON_FOLDER'], filename)
            os.makedirs(app.config['ICON_FOLDER'], exist_ok=True)
            icon.save(save_path)
            
            # 古いアイコンがデフォルトでなければ削除
            if not old_icon_is_default:
                try:
                    os.remove(os.path.join(app.config['ICON_FOLDER'], old_icon_filename))
                except FileNotFoundError:
                    pass  # ファイルが存在しない場合は無視
                except Exception as e:
                    print(f"Failed to delete old icon: {e}")

            update_fields.extend(["icon_filename=?", "icon_is_default=?"])
            update_values.extend([filename, 0])  # 0 = カスタムアイコン

        update_values.append(email)
        if update_fields:
            conn.execute(f"UPDATE users SET {', '.join(update_fields)} WHERE email=?", update_values)

        # メッセージの名前更新
        if new_name:
            conn.execute("UPDATE messages SET name=? WHERE email=?", (new_name, email))

    print("update profile successfully")
    return jsonify({"success": True})

# === メッセージ送信 ===
@app.route('/send', methods=['POST'])
def send_message():
    print("¥n¥nSending message...")
    if 'user' not in session:
        return "Unauthorized", 403

    data = request.get_json()  # ← ここを修正！
    text = data.get('text')   # ← JSON形式で受け取る
    name = data.get('name')   # ← 名前もクライアントから受け取る
    email = session['user']
    with sqlite3.connect("chat.db") as conn:
        cur = conn.execute("SELECT display_name FROM users WHERE email=?", (email,))
        row = cur.fetchone()
        name = row[0]

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        now_sec = int(datetime.now(timezone.utc).timestamp())
        conn.execute('''
            INSERT INTO messages (name, text, time, read, email)
            VALUES (?, ?, ?, 0, ?)
        ''', (name, text, now, email))
        conn.execute('''
            UPDATE users SET last_comment_time = ? WHERE email = ?''', (now_sec, email))
        
    print(f"[送信メッセージ] {text}")  # ← ターミナルに出る
    return jsonify({"status": "ok", "message": text, "time": now})

def human_readable_time(timestamp):
    if timestamp == -1:
        return "コメントなし"
    now = int(datetime.now(timezone.utc).timestamp())
    diff = now - timestamp
    if diff < 60:
        return "今"
    elif diff < 3600:
        return f"{diff // 60}分前"
    elif diff < 86400:
        return f"{diff // 3600}時間前"
    elif diff < 2592000:
        return f"{diff // 86400}日前"
    elif diff < 31536000:
        return f"{diff // 2592000}ヶ月前"
    else:
        return "ずっと前"


# === メッセージ取得 ===
@app.route('/messages')
def get_messages():
    #print("Fetching messages...")
    if 'user' not in session:
        return "Unauthorized", 403

    #email = session['user']
    messages = []
    with sqlite3.connect("chat.db") as conn:
        cur = conn.execute('''
            SELECT m.id, m.name, m.text, m.time, m.read, m.email, u.icon_filename, u.icon_is_default
            FROM messages m
            LEFT JOIN users u ON m.email = u.email
        ''')
        for row in cur.fetchall():
            messages.append({
                'id': row[0],
                'name': row[1],
                'text': row[2],
                'time': row[3],
                'read': row[4],
                'email': row[5],
                'icon_filename': row[6],
                'icon_is_default': row[7],
            })
    #print(f"Fetched {len(messages)} messages")
    return jsonify(messages)
# ログアウト
@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    resp = jsonify({"status": "ok"})
    resp.set_cookie("session", "", expires=0)  # 👈 Cookieを強制削除
    return resp

@app.route("/login")
def login_redirect():
    return redirect("/")

@app.route("/api/user-info")
def user_info():
    #print("Fetching user info...")
    uid = session.get("uid")
    if not uid:
        return jsonify({"error": "未ログイン"}), 401

    with sqlite3.connect("chat.db") as db:
        db.row_factory = sqlite3.Row
        user = db.execute("SELECT id, display_name, icon_filename, icon_is_default, email FROM users WHERE id = ?", (uid,)).fetchone()
        if not user:
            print("User not found")
            return jsonify({"error": "ユーザーが見つかりません"}), 404
        #print(f"User info fetched: {user['display_name']}, icon: {user['icon_filename']}, email: {user['email']}, is_default: {user['icon_is_default']}")
        return jsonify({
            "id": user["id"],
            "email": user["email"],
            "name": user["display_name"],
            "iconUrl": (
                "/static/default.jpeg"
                if user["icon_is_default"]
                else f"/icons/{user['icon_filename']}"
            ),    
            
            "icon_is_default": user["icon_is_default"]
        })

@app.route("/send_debug", methods=["POST"])
def receive_message():
    data = request.get_json()
    text = data.get("text")

    print(f"[受信メッセージ] {text}")  # ← ターミナルに出る
    return jsonify({"status": "ok"})

@app.route("/api/members")
def get_members():
    with sqlite3.connect("chat.db") as conn:
        cur = conn.execute("SELECT id, display_name, icon_filename, icon_is_default, last_comment_time FROM users")
        members = [{"id": r[0], "name": r[1], "icon": r[2], "icon_is_default": r[3], "last_comment_time": r[4]} for r in cur.fetchall()]
        for member in members:
            member["last_comment_time_readable"] = human_readable_time(member["last_comment_time"])
        #conn.commit()
        return jsonify(members)
    

if __name__ == '__main__':
    app.run(debug=True)
