""" 
A collection of some generic useful methods 

IMPORTANT: do not import anything other than standard libraries here, this should be usable by _everywhere_ if possible.
Specifically, do not include anything django or tracker specific, so that we
can use it in migrations, or inside the `model` files
"""

import pytz
import random

def natural_list_parse(s, symbol_only=False):
    """Parses a 'natural language' list, e.g.. seperated by commas, 
    semi-colons, 'and', 'or', etc..."""
    result = []
    tokens = [s]
    seperators = [',', ';', '&', '+']
    if not symbol_only:
        seperators += [' and ', ' or ', ' and/or ', ' vs. ']
    for sep in seperators:
        newtokens = []
        for token in tokens:
            while len(token) > 0:
                before, found, after = token.partition(sep)
                newtokens.append(before)
                token = after
        tokens = newtokens
    return list(filter(lambda x: len(x) > 0, map(lambda x: x.strip(), tokens)))


def labelify(labels):
    """reverses an array of labels to become a dictionary of indices"""
    result = {}
    for labelIndex in range(0, len(labels)):
        result[labels[labelIndex]] = labelIndex
    return result


def try_parse_int(s, base=10, val=None):
    """returns 'val' instead of throwing an exception when parsing fails"""
    try:
        return int(s, base)
    except ValueError:
        return val


def anywhere_on_earth_tz():
    """ This is a trick used by academic conference submission deadlines
    to use the last possible timezone to define the end of a particular date"""
    return pytz.timezone('Etc/GMT+12')

def make_auth_code(length=64):
    rand = random.SystemRandom()
    result = ''
    for i in range(0, length):
        result += '{:x}'.format(rand.randrange(0,16))
    return result

