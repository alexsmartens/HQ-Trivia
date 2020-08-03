import os
import logging
import eventlet
import redis
from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room

from game.modules import NEXT_GAME_ROOM, NEXT_GAME_SERVER, get_new_code, RedisSubscriptionService, UserRegistry, GameFactory


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
SERVER_INSTANCE_NAME = "SERVER" + get_new_code()
MIN_PLAYERS = 2  # Minimum number of players to start a game

# Clean up on first Heroku Dyno instance launched
redis_client.delete(NEXT_GAME_ROOM)
redis_client.delete(NEXT_GAME_SERVER)

# Create instances
user_registry = UserRegistry(redis_client, REDIS_CHANNEL_NAME,  app.logger)
game_factory = GameFactory(SERVER_INSTANCE_NAME, redis_client, MIN_PLAYERS, app.logger)

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
    Register the client to the next room in play if there is no conflict with the client name, otherwise False.

    Arguments:
        data - (dict) where the "username" key corresponds to the requested username.

    Returns:
        username - (str) the same as the username input argument if provided, an empty string otherwise.
        room_name - (str or bool) the next room in play if there is no conflict with the client name, otherwise
            False.
        msg - (str) empty if there is no conflict with the client name, otherwise an error message.

    """

    if "username" in data and isinstance(data["username"], str) and len(data["username"]):
        username, room_name, msg = game_factory.register_client(data["username"])
        if room_name:
            # Assign the user to the selected room
            # Note: join_room can only be called from a SocketIO event handler as it obtains some information from the
            # current client context (from Flask-SocketIO documentation)
            join_room(room_name)
            user_registry[request.sid] = {"username": username, "room_name": room_name}
        return username, room_name, msg
    else:
        app.logger.warning(f"Incorrect data format was received form the client {request.sid}: {data}. A correct "
                           f"message should have 'username' key and its value should be a non-empty string.")
        return "", False, '{"msg": "No user name provided, please try again", "type": "warning"}'


if __name__ == "__main__":
    socketio.run(app, debug=True)
