import time
import random
import string
import json
from collections import deque
import eventlet

import game.config_variables as conf
from game.questionnaire import QuestionManager


class GetNewCode:
    """
    Generates a code in format "iiii-xxxx-xxxx", where 'iiii' is a server count and each 'x' is a lowercase ascii
    character.
    """
    cnt = 0

    @classmethod
    def __call__(cls):
        cls.cnt = cls.cnt + 1 if cls.cnt < 9999 else 0
        letters = string.ascii_lowercase
        return f"{cls.cnt:04}-" + ''.join(random.choice(letters) if i != 4 else '-' for i in range(9))


get_new_code = GetNewCode()


class RedisSubscriptionService:
    """
    A thread-like object, that subscribes to all messages in redis and informs clients in the specified rooms and
    maintains its subscription in the background (when started). *This is a singleton.
    """
    _singleton = None

    def __new__(cls, *args, **kwargs):
        """
        Assures that class follows the singleton patter.
        """
        assert cls._singleton is None, "This class instance reinitialization is not expected"
        if not cls._singleton:
            cls._singleton = super(RedisSubscriptionService, cls).__new__(cls)
        return cls._singleton

    def __init__(self, redis_client, channel_name, socketio, logger):
        """
        Arguments:
             redis_client - (obj) redis client where the pubssub is to be subscribed to.
             channel_name - (str) redis channel where the pubssub is to be subscribed to.
             socketio - (obj) socketio app, required for sending messages to rooms.
             logger - (obj) app logger.
        """
        self.pubsub = redis_client.pubsub()
        self.pubsub.subscribe(channel_name)
        self.socketio = socketio
        self.logger = logger

    def _iter_data(self):
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

        Returns:
            None
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
        for msg_str in self._iter_data():
            eventlet.spawn(self.send, msg_str)

    def start(self):
        """
        Maintains Redis subscription in the background.
        """
        eventlet.spawn(self.run)


class UserRegistry(dict):
    """
    A dictionary-like data structure that registers clients by session id (SID) and publishes the updates via the
    specified redis_pubsub client. *This is a singleton.
    """
    _singleton = None

    def __new__(cls, *args, **kwargs):
        """
        Assures that class follows the singleton patter.
        """
        assert cls._singleton is None, "This class instance reinitialization is not expected"
        if not cls._singleton:
            cls._singleton = super(UserRegistry, cls).__new__(cls)
        return cls._singleton

    def __init__(self, redis_client, channel_name, logger):
        """
        Arguments:
             server_name - (str) name of the server instance that runs this code.
             redis_client - (obj) redis client for publishing updates about the players joining or leaving rooms.
             logger - (obj) app logger.
        """
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
        """
        Publishes updates about the players joining or leaving rooms on the specified redis channel.

        Arguments:
           action_str - (str) description of player action 'left' or 'joined';
           user_info - (dict) includes "room_name" and "username" keys with str values

        Returns:
           None
        """
        assert "room_name" in user_info and "username" in user_info, \
            f"Every published message should have at least 'room_name' and 'username'keys but this does not, " \
            f"message: {user_info}"
        # Broadcast that the new user has joined/left the group
        self.redis_client.publish(self.channel_name, json.dumps({
            "room_name": user_info["room_name"],
            "type": "players_update",
            "action": action_str,
            "username": user_info["username"],
        }))
        # Update the room records
        if action_str == "left":
            if self.redis_client.exists(user_info["room_name"], user_info["username"]):
                self.redis_client.srem(user_info["room_name"], user_info["username"])


class GameFactory:
    """
    Registers new players and creates games when enough players connected. *This is a singleton.
    """
    _singleton = None

    def __new__(cls, *args, **kwargs):
        """
        Assures that class follows the singleton patter.
        """
        assert cls._singleton is None, "This class instance reinitialization is not expected"
        if not cls._singleton:
            cls._singleton = super(GameFactory, cls).__new__(cls)
        return cls._singleton

    def __init__(self, server_name, redis_client, min_players, channel_name, logger):
        """
        Arguments:
             server_name - (str) name of the server instance that runs this code.
             redis_client - (obj) redis client for registering players and rooms.
             min_players - (int) minimum number of players for the game to start.
             channel_name - (str) redis channel where game instances publish questions to.
             logger - (obj) app logger.
        """
        self.server_name = server_name
        self.redis_client = redis_client
        self.min_players = min_players
        self.channel_name = channel_name
        self.logger = logger

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
            other_players - (set) other players in waiting for the next game if there is no conflict with the client
                name, otherwise an empty set.
            min_players - (int) minimum players to start a new game if there is no conflict with the client name, otherwise 0.
            is_game_starting - (bool) whether a new game was created, this depends on what the player sees when he/she
                logs in.
            msg - (json_str) empty if there is no conflict with the username, otherwise a json_str with two attributes
                where (1) "msg" is a message asking to pick a different name and (2) "type" is "info".
        """
        # next_room_in is checked every time because it might be updated by a different server instance. It happens if
        # a different server has started the previous game, then the player is to be enrolled to the most recent
        # game room
        next_room = self._get_next_game_room()

        if self.redis_client.sismember(next_room, username):
            # Client with this name is already registered
            return username, False, set(), self.min_players, False, '{' \
                '"msg": "This username already exists, please pick a different one", ' \
                '"type": "info"' \
                '}'
        else:
            if self.min_players - self.redis_client.scard(next_room) <= 1:
                # Spawn a new game
                if self.redis_client.exists(conf.NEXT_GAME_SERVER):
                    pass
                else:
                    # Register this server instance to run the next game
                    self.redis_client[conf.NEXT_GAME_SERVER] = self.server_name
                    # Create a new game
                    eventlet.spawn(self.create_new_game, next_room)
            other_players = self.redis_client.smembers(next_room)
            self.redis_client.sadd(next_room, username)
            return username, next_room, other_players, self.min_players, self.redis_client.exists(conf.NEXT_GAME_SERVER), ""

    def _get_next_game_room(self):
        """"
        Gets the room name that will be in play next from redis. Creates a new room name if there is no info about the
        next room in play.

        Returns:
            room_name - the room that will be in play next.
        """
        if self.redis_client.exists(conf.NEXT_GAME_ROOM):
            pass
        else:
            self.redis_client[conf.NEXT_GAME_ROOM] = "room-" + get_new_code()
        return self.redis_client[conf.NEXT_GAME_ROOM]

    def create_new_game(self, room_name):
        new_game = Game(room_name, self.redis_client, self.channel_name, self.logger)
        new_game.start()


class Game:
    """
    A thread-like object, that plays the game for the registered players.
    """
    def __init__(self, room_name, redis_client, channel_name, logger):
        """
        Arguments:
            room_name - (str) the game room name, only players who joined this room are in this game. Also, a redis
                value stored by the room name has a set of all players in the game at any moment of time, including
                prior to the game start and during the game.
            redis_client - (obj) redis client for game messages communication.
            channel_name - (str) redis channel the game messages are published to.
            logger - (obj) app logger.
        """
        self.room_name = room_name
        self.redis_client = redis_client
        self.channel_name = channel_name
        self.logger = logger
        # Game info
        self.round_cnt = 0
        self.players = set()
        eventlet.spawn(self._get_payers)
        self.question_q = QuestionManager(self.redis_client, self.logger)

    def _get_payers(self):
        self.players = self.redis_client.smembers(self.room_name)

    def _run_new_round(self, round_timer):
        """"
        Runs a round of game for the players registered in this game (room). This includes asking a question, collecting
        the answers, removing players who answered incorrectly from the game, and prompting results back to the users.

        Arguments:
            round_timer - (int) available time in seconds for answering a question.

        Returns:
            players_in_game - (int) number of players who are still in the game (submitted the correct answers).
        """
        self.round_cnt += 1

        # Initialize the info required to run a new round
        question = self.question_q.pop()
        if len(question["question"]) == 0:
            self.logger.error("CRITICAL ERROR: not enough questions for a round to run")
        # Players' answers are to be submitted to the hash table with the round key below. When submitting, the hash
        # is the player username and the value is the question answer
        round_answer_key = f"{self.room_name}-ROUND-{self.round_cnt}-ANSWERS"

        # Launch a new round
        eventlet.spawn(self._publish, {"type": "new_round",
                                       "question": question["question"],
                                       "options": question["options"],
                                       "round_answer_key": round_answer_key,
                                       "timer": round_timer,
                                       "round": self.round_cnt,
                                       "room": self.room_name,
                                       })
        # Update players in the game
        eventlet.spawn(self._get_payers)
        # Wait until the round is ended
        eventlet.sleep(round_timer)

        # Get players' answers
        answers = self.redis_client.hgetall(round_answer_key)

        # Initialize round statistics accounting
        answer_cnt = 0  # Total number of answers received
        correct_cnt = 0  # Total number of correct answers received
        option_cnt = dict.fromkeys(question["options"], 0)  # Total number of answers received for every option
        correct_answer = question["answer"]

        # Compute round statistics
        players_submitted = set()
        for username, answer in answers.items():
            players_submitted.add(username)
            if answer in option_cnt:
                option_cnt[answer] += 1
                if answer == correct_answer:
                    correct_cnt += 1
                else:
                    # Broadcast players who submitted incorrect answers and remove them form the game
                    eventlet.spawn(self._publish, {
                        "type": "players_update",
                        "action": "left",
                        "username": username,
                    })
                answer_cnt += 1
            else:
                self.logger.error(f"Player's answer does not match any available options, username: {username}, "
                                  f"answer: {answer}, available options: {question['options'].keys()}")
        # Update stat with the players who did not submit their answers
        for username in self.players.difference(players_submitted):
            answer_cnt += 1
            # Broadcast players who did not submit their answers and remove them form the game
            eventlet.spawn(self._publish, {
                "type": "players_update",
                "action": "left",
                "username": username,
            })

        # Prepare option stats as ratios
        option_stats = {option: cnt/answer_cnt if answer_cnt else 0 for option, cnt in option_cnt.items()}
        # Inform all players (no matter they lose or win) about the round results
        eventlet.spawn(self._publish, {
            "type": "round_stats",
            "round": self.round_cnt,
            "options": question["options"],
            "stats": option_stats,
            "correct_answer": correct_answer,
            "players_in_game": correct_cnt,
        })
        # Clean up the hash table for recording the round answers
        self.redis_client.delete(round_answer_key)
        return correct_cnt

    def _publish(self, info):
        """
        Publishes round updates. Also, removes players who submitted incorrect answers from the game room (if "left"
        action provided).

        Arguments:
           info - (dict) includes "type" and possibly some other game related keys.

        Returns:
           None
        """
        assert "type" in info, f"Every published message should have at least 'type' keys but this does not, message: {info}"
        info["room_name"] = self.room_name
        # Broadcast the received info
        self.redis_client.publish(self.channel_name, json.dumps(info))
        # Remove the user from this game if asked
        if "action" in info and info["action"] == "left":
            assert "username" in info, "Username should be provided on 'left' action str"
            if self.redis_client.exists(self.room_name, info["username"]):
                self.redis_client.srem(self.room_name, info["username"])

    def run(self, game_timer=10, round_timer=10):
        """"
        Runs a series of rounds until there is only one player left.

        Arguments:
            game_timer - (int) available time in seconds for joining a game by other players.
            round_timer - (int) available time in seconds for answering a question in each round.

        Returns:
            None
        """

        # Notify players about starting new game
        eventlet.spawn(self._publish, {"type": "new_game", "timer": game_timer})
        # Wait until it is time to start the game
        eventlet.sleep(game_timer)

        # Stop users from joining this game
        self.redis_client.delete(conf.NEXT_GAME_ROOM)
        self.redis_client.delete(conf.NEXT_GAME_SERVER)

        eventlet.sleep(2)  # Allow the latest players to get ready
        # Run rounds until there are more than one player in the game
        players_in_game = 2
        while players_in_game > 1:
            players_in_game = self._run_new_round(round_timer)
            eventlet.sleep(10)  # Delay between rounds

        # Clean up the set for keeping track of the users in game
        self.redis_client.delete(self.room_name)

        # Keep track of how many rounds players completed for future question selection
        self.logger.info(f"Game ends in {self.round_cnt} rounds")

    def start(self):
        """
        Starts the game asynchronously.
        """
        eventlet.spawn(self.run)

