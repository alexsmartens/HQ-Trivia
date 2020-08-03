import random
import string
import json
import eventlet


# Redis key names shared between server instances
NEXT_GAME_ROOM = "next_game_room"  # this key's redis value defines the room_name where the next game will be played
NEXT_GAME_SERVER = "next_game_server"  # this key's redis value defines the server instance that will run the next game (if any)


def get_random_code():
    """
    Generates a random code in format "xxxx-xxxx", where 'x' is a lowercase ascii character.
    """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) if i != 4 else '-' for i in range(9))


class RedisSubscriptionService:
    """
    A thread-like  object, that subscribes to all messages in redis and informs clients in the specified rooms and
    maintains its subscription in the background (when started).
    """

    def __init__(self, redis_client, channel_name, socketio, logger):
        self.pubsub = redis_client.pubsub()
        self.pubsub.subscribe(channel_name)
        self.socketio = socketio
        self.logger = logger

    def __iter_data(self):
        """
        Returns redis posts of data type "message" when they are published.

        Returns:
            msg_str - (str) a JSON with the message content.
        """
        for post in self.pubsub.listen():
            if post["type"] == "message":
                msg_str = post.get("data")
                yield msg_str

    def send(self, msg_str):
        """
        Sends out the message.

        Arguments:
            msg_str - (str) a JSON with the message content. This string should be a JSON string and contain at least
                two keys "room_name" (intended destination), and "type" (message type)

        """
        try:
            msg = json.loads(msg_str)
        except json.decoder.JSONDecodeError:
            self.logger.error(f"Incorrect message format was read: {msg_str}. A correct message should be a "
                              f"JSON string")
        else:
            if "type" in msg and "room_name" in msg:
                room_name = msg["room_name"]
                del msg["room_name"]
                self.socketio.send(msg, room=room_name)
            else:
                self.logger.warning(f"Incorrect message format was read: {msg_str}. A correct message should have "
                                    f"'room_name' and 'type' keys")

    def run(self):
        """
        Listens for new messages and sends them to the specified rooms
        """
        for msg_str in self.__iter_data():
            eventlet.spawn(self.send, msg_str)

    def start(self):
        """
        Maintains Redis subscription in the background.
        """
        eventlet.spawn(self.run)


class UserRegistry(dict):
    """
    A dictionary-like data structure that registers clients by session id (SID) and publishes the updates via the
    specified redis_pubsub client.
    """
    def __init__(self, redis_client, channel_name, logger):
        super().__init__()
        self.redis_client = redis_client
        self.channel_name = channel_name
        self.logger = logger

    def __setitem__(self, session_id, user_info):
        eventlet.spawn(self._publish, "joined", user_info)
        super().__setitem__(session_id, user_info)

    def __delitem__(self, session_id):
        eventlet.spawn(self._publish, "left", self.get(session_id).copy())
        super().__delitem__(session_id)

    def _publish(self, action_str, user_info):
        # Broadcast that the new user has joined/left the group
        self.redis_client.publish(self.channel_name, json.dumps({
            "room_name": user_info["room_name"],
            "type": "players_update",
            "action": action_str,
            "username": user_info['username'],
        }))


class GameFactory:
    """
    Tracks new client connections and create games when enough clients connected.
    """
    def __init__(self, server_name, redis_client, min_players, logger):
        self.server_name = server_name
        self.redis_client = redis_client
        self.min_players = min_players
        self.logger = logger
        self.room_name = self._get_room_registration()

    def register_player(self, username):
        """"
        Registers a player to the game (next_room_in) in redis. This function launches a new game if the minimum number
        of players is reached.

        Arguments:
            username - (str) desired username.

        Returns:
            username - (str) the same as the username input argument.
            room_name - (str or bool) the next room in play if there is no conflict with the username, otherwise
                False.
            msg - (json_str) empty if there is no conflict with the username, otherwise a json_str with two attributes
                where (1) "msg" is a message asking to pick a different name and (2) "type" is "info"
        """
        # next_room_in is checked every time because it might be updated by a different server instance. It happens if
        # a different server has started the previous game, then the player is to be enrolled to the most recent
        # game room
        next_room = self._get_next_game_room()

        if self.redis_client.sismember(next_room, username):
            # Client with this name is already registered
            return username, False, '{' \
                                    '"msg": "This username already exists, please pick a different one", ' \
                                    '"type": "info"' \
                                    '}'
        else:
            if self.min_players - self.redis_client.scard(next_room) <= 1:
                # Spawn a new game
                if self.redis_client.exists(NEXT_GAME_SERVER):
                    pass
                else:
                    # Register this server instance to run the next game
                    self.redis_client[NEXT_GAME_SERVER] = self.server_name
                    # *********** spawn the next game here
                    raise NotImplemented
            self.redis_client.sadd(next_room, username)
            return username, next_room, ""

    def _get_next_game_room(self):
        """"
        Gets the room name that will be in play next from redis. Creates a new room name if there is no info about the
        next room in play.

        Returns:
            room_name - the room that will be in play next.
        """
        if self.redis_client.exists(NEXT_GAME_ROOM):
            pass
        else:
            self.redis_client[NEXT_GAME_ROOM] = "room-" + get_random_code()
        return self.redis_client[NEXT_GAME_ROOM]
