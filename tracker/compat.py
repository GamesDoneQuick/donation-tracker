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
