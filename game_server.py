import os
import logging
import eventlet
import redis
from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room

from game.modules import get_random_code


# Initialize the app
app = Flask(__name__)
app.config["SECRET_KEY"] = "89dfg-lkdf3-892ls-ljg06"  # Used for signing the session cookies
socketio = SocketIO(app)
# Configure logger
gunicorn_logger = logging.getLogger("gunicorn.error")
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)
# Configure redis
REDIS_URL = os.environ.get("REDIS_URL")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)
redis_pubsub = redis.pubsub()

# Configure the game server
SERVER_INSTANCE_NAME = "SERVER" + get_random_code()
MIN_PLAYERS = 2  # Minimum number of players to start a game


@app.route("/")
def load_web_page():
    """
    Returns the main html page.
    """
    return render_template("index.html")


if __name__ == "__main__":
    socketio.run(app, debug=True)
