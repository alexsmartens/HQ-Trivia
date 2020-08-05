# 'questions_1' were borrowed form https://github.com/joebandenburg/fibbage-questions/blob/master/questions.json

import json
import random
from collections import deque
import eventlet

import game.config_variables as conf


def get_random_set(set_len, start, end):
    """
    Gets a set of random numbers in the range of [start, end).

    Arguments:
        start - (int) starting number.
        end - (int) end number.
        set_len - (int) length of the set to be generated.

    Returns:
        numbers - (set) set of random numbers.
    """
    numbers = set()
    while len(numbers) < set_len:
        rnd = random.randint(start, end-1)
        if rnd in numbers:
            pass
        else:
            numbers.add(rnd)
    return numbers


def load_questions2redis(redis_client, file_path=None, file_ext=None, category_dict=None):
    """
    Loads questions from a file to the specified redis hash maps, where each question category corresponds to a separate
    hash map. In a hash map, a hash is a question count number (from 0 to N) and a value is a JSON string in a
    specified format.

    Notes:
        (1) Each question JSON str should have the following keys
            - 'category',
            - 'question',
            - 'answer',
            - 'alternateSpellings',
            - 'suggestions'.
        (2) Only supports JSON files at the moment.

    Arguments:
        redis_client - (obj) redis client, to where the data is to be loaded.
        file_path - (str) local path to the file to be loaded including the file name and excluding the extension.
        file_ext - (str) file extension, e.g., 'json', 'csv'.
        category_dict - (dict) a dictionary that shows where to map a category from the file to the redis_client,
            e.g., {'questionnaire_field': 'redis_field'}

    Returns:
        None
    """
    assert (file_path is None) and (file_ext is None) and (category_dict is None), \
        "Only expected to work with the default values at the moment"
    file_path = "./questions/questions_1" if file_path is None else file_path
    file_ext = "json" if file_ext is None else file_ext
    category_dict = {
        "normal": conf.NORMAL_QUESTIONS,
        "final": conf.FINAL_QUESTIONS,
    } if category_dict is None else category_dict

    if file_ext == "json":
        with open(f"{file_path}.{file_ext}") as f:
            questions = json.load(f)
    else:
        raise NotImplemented

    for q_key, redis_key in category_dict.items():
        for idx, question in enumerate(questions[q_key]):
            assert ("category" in question) and \
                   ("question" in question) and \
                   ("answer" in question) and \
                   ("alternateSpellings" in question) and \
                   ("suggestions" in question), \
                f"One or more keys are missing the selected JSON string question, the expected keys are 'category', " \
                f"'question', 'answer', 'alternateSpellings', 'suggestions'. The encountered question: {question}"
            question["question"] = question["question"].replace("<BLANK>", " _______ ")
            redis_client.hset(redis_key, idx, json.dumps(question))
    del questions


def map_question_str2dict(question_str, q_hash):
    """
    Maps a JSON string to a dictionary which is ready to be played.

     Arguments:
         question_str - (str) question in the JSON string format (includes the following keys:
            'category', 'question', 'answer', 'alternateSpellings', 'suggestions').
         q_hash - (str or int) the question hash in the corresponding hash map.

     Returns:
         question - (dict) a question dictionary ready to by played, which includes a "question", a correct "answer",
            3 "options" including the correct option and the question index in the database "hash_idx".
     """
    question_raw = json.loads(question_str)
    assert ("category" in question_raw) and \
           ("question" in question_raw) and \
           ("answer" in question_raw) and \
           ("alternateSpellings" in question_raw) and \
           ("suggestions" in question_raw), \
        f"One or more keys are missing the selected JSON string question, the expected keys are 'category', " \
        f"'question', 'answer', 'alternateSpellings', 'suggestions'. The encountered question: {question_raw}"
    assert isinstance(q_hash, int) or isinstance(q_hash, str), "Question hash should be integer or string"

    question = {}
    question["hash"] = q_hash
    question["question"] = question_raw["question"]
    question["answer"] = question_raw["answer"] if len(question_raw["alternateSpellings"]) == 0 or random.randint(0, 1) == 0\
        else random.choice(question_raw["alternateSpellings"])
    question["options"] = random.sample(question_raw["suggestions"], 2) + [question["answer"]]
    random.shuffle(question["options"])
    return question


def get_random_questions(redis_client, redis_key, q_len):
    """
     Gets a list of random questions of the specified difficulty from redis.

     Note:
         Assumes that question hashes are the question indices (this is how load_questions2redis loads questions to redis).

     Arguments:
         redis_client - (obj) redis client, where the questions are to be read.
         redis_key - (str) the redis key to the questions hash map.
         q_len - (int) number of questions to be returned.

     Returns:
         q_hashes - (set) set of the question hashes (for assuring that the game does not run the same question twice
            if additional questions are polled during the game).
         q_queue - (deque) queue of question. Each question is stored in a dictionary format, with the following
            keys: "question", "options", "answer", "hash_idx"

     """
    num_questions = redis_client.hlen(redis_key)
    q_hashes = get_random_set(q_len, 0, num_questions)
    json_questions = redis_client.hmget(redis_key, *q_hashes)
    q_queue = deque()
    for i, q_hash in enumerate(q_hashes):
        q_queue.append(map_question_str2dict(json_questions[i], q_hash))
    return q_hashes, q_queue


class QuestionManager:
    """
    A queue-like object, that gets questions from redis and provides an easy access to them through "pop" method. It
    also controls the number of questions in the queue and gets more questions if needed.
    """

    def __init__(self, redis_client, logger, min_questions=5, question_config=None, update_lim=10):
        """
        Arguments:
             redis_client - (obj) redis client where get the questions.
                          logger - (obj) app logger.
             min_questions - (int) minimum number of questions that should be in the queue at all times.
             question_config - (dict) a dictionary in which the keys are the keys of redis hash maps where the questions
                are to be drawn from and and the values are the numbers of questions to be drawn from each hash map,
                e.g., {"normal": 10, "final": 5}, {"nature": 2, "history": 3} .
            update_lim - (int) maximum allowed number of updates (this limit is supposed to cover a case when a user has
                seen all the questions from the database; alternatively but unlikely, it might harm (1) if the user is a
                genius and knows all the answers or (2) bad luck with getting random questions)
        """
        self.redis_client = redis_client
        self.logger = logger
        self.min_questions = min_questions
        self.question_config = {
            conf.NORMAL_QUESTIONS: 10,
            conf.FINAL_QUESTIONS: 5,
        } if question_config is None else question_config
        # Keeping track of the game questions
        self.questions_q = deque()
        self.question_idx_ctrl = {key: set() for key in self.question_config}
        # Control number of updates
        self._update_lim = update_lim
        self.update_count = 0
        # Prepare questions in the background
        eventlet.spawn(self._prepare_game_questions)

    def __len__(self):
        """
        Propagates the actual question queue length as the object length
        """
        return len(self.questions_q)

    def _prepare_game_questions(self):
        """"
         Adds more questions to question queue (self.questions_q) and keeps track of the added questions
         in self.question_idx_ctrl.

         Note:
             The function only does what it is supposed to do if no run count limit (self._update_lim) is reached.
         """
        if self.update_count < self._update_lim:
            for redis_hash, q_len in self.question_config.items():
                q_hashes, q_queue = get_random_questions(self.redis_client, redis_hash, q_len)
                if len(self.question_idx_ctrl[redis_hash]) == 0:
                    self.question_idx_ctrl[redis_hash] = q_hashes
                    while q_queue:
                        self.questions_q.append(q_queue.pop())
                else:
                    while q_queue:
                        question = q_queue.pop()
                        if question["hash"] in self.question_idx_ctrl[redis_hash]:
                            pass
                        else:
                            self.question_idx_ctrl[redis_hash].add(question["hash"])
                            self.questions_q.append(question)
            self.update_count += 1
        else:
            self.logger.error(f"Exceeded maximum number of question updates in a game (limit = {self._update_lim})")

    def pop(self):
        """
        Pops an item from the question queue. It also launches a question update if the number of questions in a queue
        is lower than the limit (self.min_questions).

        Returns:
             question - (dict) first question in the queue (self.questions_q), this question has the following keys:
                "question", "options", "answer", "hash_idx" (as per map_question_str2dict specification).
        """
        if len(self.questions_q) -1 < self.min_questions:
            eventlet.spawn(self._prepare_game_questions)
        return self.questions_q.pop()
