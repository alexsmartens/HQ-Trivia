import os
import logging
import eventlet
import redis
from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room

from game.modules import get_random_code, RedisSubscriptionService


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


# Run in the background
redis_subscription = RedisSubscriptionService(redis_client, REDIS_CHANNEL_NAME, socketio, app.logger)
redis_subscription.start()


if __name__ == "__main__":
    socketio.run(app, debug=True)
