import logging
import eventlet
from flask import Flask, render_template, request
from flask_socketio import SocketIO


# Initialize the app
app = Flask(__name__)
app.config["SECRET_KEY"] = "89dfg-lkdf3-892ls-ljg06"  # Used for signing the session cookies
socketio = SocketIO(app)
# Configure logger
gunicorn_logger = logging.getLogger("gunicorn.error")
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)


@app.route("/")
def load_web_page():
    return render_template("index.html")


if __name__ == "__main__":
    socketio.run(app, debug=True)
