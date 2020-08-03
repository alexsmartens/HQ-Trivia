import os

# Configure redis
REDIS_CHANNEL_NAME = "hq_trivia"
REDIS_URL = os.environ.get("REDIS_URL")

# Redis key names shared between server instances
NEXT_GAME_ROOM = "next_game_room"  # this key's redis value defines the room_name where the next game will be played
NEXT_GAME_SERVER = "next_game_server"  # this key's redis value defines the server instance that will run the next game (if any)
NORMAL_QUESTIONS = "questions_normal"
FINAL_QUESTIONS = "questions_final"
