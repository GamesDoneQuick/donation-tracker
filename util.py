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

def make_rand(rand_source=None, rand_seed=None):
    if rand_source is None:
        if rand_seed is None:
            rand_source = random.SystemRandom()
        else:
            rand_source = random.Random(rand_seed)
    return rand_source
    
def make_auth_code(length=64, rand_source=None, rand_seed=None):
    rand_source = make_rand(rand_source, rand_seed)
    result = ''
    for i in range(0, length):
        result += '{:x}'.format(rand_source.randrange(0,16))
    return result

def random_num_replace(s, replacements, rand_source=None, rand_seed=None, max_length=None):
    """Attempts to 'uniquify' a string by adding/replacing characters with a hex string 
    of the specified length"""
    rand_source = make_rand(rand_source, rand_seed)
    if max_length is None:
        max_length = len(s) + replacements
    if max_length < replacements:
        raise Exception("Error, max_length ({0}) was less than the number of requested replacements ({1})".format(max_length, replacements))
    originalLength = len(s)
    endReplacements = min(max_length - len(s), replacements)
    s += make_auth_code(endReplacements, rand_source=rand_source)
    if endReplacements < replacements:
        replacementsLeft = replacements-endReplacements
        s = s[:originalLength-replacementsLeft] + make_auth_code(replacementsLeft, rand_source) + s[originalLength:]
    return s