from inspect import signature


def reverse(*args, query=None, fragment=None, **kwargs):
    # TODO: remove when 5.2 is the oldest supported Django version
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
