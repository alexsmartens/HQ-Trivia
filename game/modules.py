import random
import string
import json
import eventlet


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
