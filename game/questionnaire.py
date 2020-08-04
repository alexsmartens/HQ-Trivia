# 'questions_1' were borrowed form https://github.com/joebandenburg/fibbage-questions/blob/master/questions.json

import json
import random
from collections import deque

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
            question["question"] = question["question"].replace("<BLANK>", "_______")
            redis_client.hset(redis_key, idx, json.dumps(question))
    del questions


def map_question_str2dict(question_str):
    """
    Maps a JSON string to a dictionary which is ready to be played.

     Arguments:
         question_str - (str) question in the JSON string format (includes the following keys:
            'category', 'question', 'answer', 'alternateSpellings', 'suggestions').

     Returns:
         question - (dict) a question dictionary ready to by played, which includes a "question", a correct "answer" and
            3 "options" including the correct option.
     """
    question_raw = json.loads(question_str)
    assert ("category" in question_raw) and \
           ("question" in question_raw) and \
           ("answer" in question_raw) and \
           ("alternateSpellings" in question_raw) and \
           ("suggestions" in question_raw), \
        f"One or more keys are missing the selected JSON string question, the expected keys are 'category', " \
        f"'question', 'answer', 'alternateSpellings', 'suggestions'. The encountered question: {question_raw}"

    question = {}
    question["question"] = question_raw["question"]
    question["answer"] = question_raw["answer"] if len(question_raw["alternateSpellings"]) == 0 or random.randint(0, 1) == 0\
        else random.choice(question_raw["alternateSpellings"])
    question["options"] = random.sample(question_raw["suggestions"], 2) + [question["answer"]]
    random.shuffle(question["options"])
    return question


def get_random_questions(redis_client, difficulty_level, q_len):
    """
     Gets a list of random questions of the specified difficulty from redis.

     Note:
         This function treats redis questions as they all are in the same JSON string format as the ones in "questions_1.json".

     Arguments:
         redis_client - (obj) redis client, where the questions are to be read.
         difficulty_level - (str) the redis key to the questions with the specified difficulty.
         q_len - (int) number of questions to be returned.

     Returns:
         indices - (set) set of the question indices (for assuring that the game does not run the same question twice
            if additional questions are polled during the game).
         question_q - (deque) queue of question. Each question is stored in a dictionary format, with the following
            keys: "question", "options", "answer".

     """
    num_questions = redis_client.hlen(difficulty_level)
    indices = get_random_set(q_len, 0, num_questions)
    questions_json = redis_client.hmget(difficulty_level, *indices)
    question_q = deque()
    for question_json in questions_json:
        question_q.append(map_question_str2dict(question_json))
    return indices, question_q
