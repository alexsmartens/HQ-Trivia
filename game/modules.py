import random
import string


def get_random_code():
    """
    Generates a random code in format "xxxx-xxxx", where 'x' is a lowercase ascii character.
    """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) if i != 4 else '-' for i in range(9))
