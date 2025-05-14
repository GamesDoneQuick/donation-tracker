from inspect import signature

try:
    from itertools import pairwise
except ImportError:
    # TODO: remove when 3.10 is oldest supported version

    def pairwise(iterable):
        import itertools

        # pairwise('ABCDEFG') --> AB BC CD DE EF FG
        a, b = itertools.tee(iterable)
        next(b, None)
        return zip(a, b)


def reverse(*args, query=None, fragment=None, **kwargs):
    from django.urls import reverse

    sig = signature(reverse)
    if 'query' in sig.parameters:
        return reverse(*args, query=query, fragment=fragment, **kwargs)
    else:
        import urllib.parse

        parts = urllib.parse.urlsplit(reverse(*args, **kwargs))
        return urllib.parse.urlunparse(
            (
                *parts[:4],
                urllib.parse.urlencode(query or {}),
                urllib.parse.quote_plus(fragment or ''),
            )
        )
