# 'questions_1' were borrowed form https://github.com/joebandenburg/fibbage-questions/blob/master/questions.json

import json
import random

import game.config_variables as conf


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
                "One or more keys are missing the selected JSON string question, the expected keys are 'category', " \
                "'question', 'answer', 'alternateSpellings', 'suggestions'"
            redis_client.hset(redis_key, idx, json.dumps(question))
    del questions
