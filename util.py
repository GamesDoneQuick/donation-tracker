""" 
A collection of some generic useful methods 

IMPORTANT: do not import anything other than standard libraries here, this should be usable by _everywhere_ if possible
"""

# Parses a 'natural language' list, i.e. seperated by commas, semi-colons, and 'and's
def natural_list_parse(s, symbol_only=False):
  result = []
  tokens = [s]
  seperators = [',',';','&','+']
  if not symbol_only:
    seperators += [' and ',' or ', ' and/or ', ' vs. ']
  for sep in seperators:
    newtokens = []
    for token in tokens:
      while len(token) > 0:
        before, found, after = token.partition(sep)
        newtokens.append(before)
        token = after
    tokens = newtokens
  return list(filter(lambda x: len(x) > 0, map(lambda x: x.strip(), tokens)))
  
# reverses an array of labels to become a dictionary of indices
def labelify(labels):
    result = {}
    for labelIndex in range(0, len(labels)):
        result[labels[labelIndex]] = labelIndex
    return result

# returns 'val' instead of throwing an exception when parsing fails
def try_parse_int(s, base=10, val=None):
    try:
        return int(s, base)
    except ValueError:
        return val
        