from flask import Flask, render_template
from flask_socketio import SocketIO, send, emit

app = Flask(__name__)
socketio = SocketIO(app)

# WebSocket接続時に呼ばれるイベント
@socketio.on('connect')
def on_connect():
    print('クライアントが接続されました')
    #send("サーバーに接続しました！", broadcast=True)
    emit('connected',{"msg": "サーバーに接続しました！"})

# メッセージを受信して、送信するイベント
@socketio.on('message')
def handle_message(msg):
    print(f"メッセージ受信: {msg}")
    #send(f"サーバーからの返信: {msg}")
    emit('message',{"msg": f"サーバーからの返信: {msg}"})

# Flaskアプリのルート
@app.route('/')
def index():
    return render_template('simple_socket.html')

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000)
