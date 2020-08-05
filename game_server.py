import os
import logging
import eventlet
import redis
from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room

import game.config_variables as conf
from game.questionnaire import load_questions2redis
from game.modules import get_new_code, RedisSubscriptionService, UserRegistry, GameFactory


# Initialize the app
app = Flask(__name__)
app.config["SECRET_KEY"] = "89dfg-lkdf3-892ls-ljg06"  # Used for signing the session cookies
socketio = SocketIO(app)
# Configure logger
gunicorn_logger = logging.getLogger("gunicorn.error")
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)
# Configure redis
redis_client = redis.from_url(conf.REDIS_URL, decode_responses=True)

# Configure the game server
SERVER_INSTANCE_NAME = "SERVER" + get_new_code()
MIN_PLAYERS = 2  # Minimum number of players to start a game

# Clean up on first Heroku Dyno instance launched
redis_client.delete(conf.NORMAL_QUESTIONS)
redis_client.delete(conf.NEXT_GAME_SERVER)
redis_client.delete(conf.NEXT_GAME_ROOM)
redis_client.delete(conf.NEXT_GAME_SERVER)
# Set up questionnaire
load_questions2redis(redis_client)

# Create instances
user_registry = UserRegistry(redis_client, conf.REDIS_CHANNEL_NAME,  app.logger)
game_factory = GameFactory(SERVER_INSTANCE_NAME, redis_client, MIN_PLAYERS, conf.REDIS_CHANNEL_NAME, app.logger)

# Run in the background
redis_subscription = RedisSubscriptionService(redis_client, conf.REDIS_CHANNEL_NAME, socketio, app.logger)
redis_subscription.start()


@app.route("/")
def load_web_page():
    """
    Returns the main html page.
    """
    return render_template("index.html")


@socketio.on("disconnect")
def disconnect():
    """
    Removes user registration, if the user with the specified SID (request.sid) has been registered in a game.
    """
    if request.sid in user_registry:
        del user_registry[request.sid]


@socketio.on("register_client")
def register_client(data):
    """
    Register the client to the next room in play if there is no conflict with the client name, otherwise False.

    Arguments:
        data - (dict) with only one key, "username", which value is the requested username.

    Returns (the front end callback gets the returned values):
        username - (str) the same as the username input argument if provided, an empty string otherwise.
        room_name - (str or bool) the next room in play if there is no conflict with the client name, otherwise
            False.
        other_players - (dict) other players in the game, such as all the values in this dist are 0 because
            the original data structure, set, is not serializable. An empty dictionary is returned if there is a
            conflict with the client name or an error.
        min_players - (int) minimum players to start a new game if there is no conflict with the client name, otherwise 0.
        is_game_starting - (bool) whether a new game was created, this depends on what the player sees when he/she
                logs in.
        msg - (str) empty if there is no conflict with the client name, otherwise an error message.

    """

    if "username" in data and isinstance(data["username"], str) and len(data["username"]):
        username, room_name, other_players, min_players, is_game_starting, msg = game_factory.register_player(data["username"])
        if room_name:
            # Assign the user to the selected room
            # Note: join_room can only be called from a SocketIO event handler as it obtains some information from the
            # current client context (from Flask-SocketIO documentation)
            join_room(room_name)
            user_registry[request.sid] = {"username": username, "room_name": room_name}
        return username, room_name, dict.fromkeys(other_players, 0), min_players, is_game_starting, msg
    else:
        app.logger.warning(f"Incorrect data format was received form the client {request.sid}: {data}. A correct "
                           f"message should have 'username' key and its value should be a non-empty string.")
        return "", False, {}, 0, False, '{"msg": "No user name provided, please try again", "type": "warning"}'


@socketio.on("report_round_answer")
def register_player_answer(data):
    """
    Register the player answer in the corresponding round.

    Arguments:
        data - (dict) with the following keys:
            "round_answer_key" - a redis hash map key, where the answer is to be registered;
            "username" - player's name, a key for registering the answer in the hash map;
            "answer" - user's answer, a value for the corresponding key

    Returns:
        None
    """
    redis_client.hset(data["round_answer_key"], data["username"], data["answer"])


if __name__ == "__main__":
    socketio.run(app, debug=True)
