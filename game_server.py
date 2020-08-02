import eventlet
# Recommended by Flask-SocketIO: https://flask-socketio.readthedocs.io/en/latest/#using-nginx-as-a-websocket-reverse-proxy
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO


# Initialize the app
app = Flask(__name__)
app.config["SECRET_KEY"] = "89dfg-lkdf3-892ls-ljg06"  # Used for signing the session cookies
socketio = SocketIO(app)


@app.route("/")
def load_web_page():
    return render_template("index.html")


if __name__ == "__main__":
    socketio.run(app, debug=True)
