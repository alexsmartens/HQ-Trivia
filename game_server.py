import os
import logging
import eventlet
import redis
from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room

from game.modules import get_random_code, RedisSubscriptionService, UserRegistry


# Initialize the app
app = Flask(__name__)
app.config["SECRET_KEY"] = "89dfg-lkdf3-892ls-ljg06"  # Used for signing the session cookies
socketio = SocketIO(app)
# Configure logger
gunicorn_logger = logging.getLogger("gunicorn.error")
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)
# Configure redis
REDIS_CHANNEL_NAME = "hq_trivia"
REDIS_URL = os.environ.get("REDIS_URL")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Configure the game server
SERVER_INSTANCE_NAME = "SERVER" + get_random_code()
MIN_PLAYERS = 2  # Minimum number of players to start a game

# Create instances
user_registry = UserRegistry(redis_client, REDIS_CHANNEL_NAME,  app.logger)

# Run in the background
redis_subscription = RedisSubscriptionService(redis_client, REDIS_CHANNEL_NAME, socketio, app.logger)
redis_subscription.start()


@app.route("/")
def load_web_page():
    """
    Returns the main html page.
    """
    return render_template("index.html")


@socketio.on("register_client")
def register_client(data):
    """
    Register the client.

    """

    if "username" in data and isinstance(data["username"], str) and len(data["username"]):
        return data["username"], "sample-room", ""
    else:
        app.logger.warning(f"Incorrect data format was received form the client {request.sid}: {data}. A correct "
                           f"message should have 'username' key and its value should be a non-empty string.")
        return "", False, '{"msg": "No user name provided, please try again", "type": "warning"}'


if __name__ == "__main__":
    socketio.run(app, debug=True)
