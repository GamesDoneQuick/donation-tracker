from functools import wraps

from django.http import HttpResponsePermanentRedirect


def strip_args(positional=0, keywords=None):
    keywords = keywords or []

    def _inner(view_func):
        @wraps(view_func)
        def decorator(*args, **kwargs):
            return view_func(
                *args[positional:],
                **{k: v for k, v in kwargs.items() if k not in keywords},
            )

        return decorator

    return _inner


def no_querystring(view_func):
    @wraps(view_func)
    def decorator(request, *args, **kwargs):
        if request.GET:
            return HttpResponsePermanentRedirect(request.path)
        return view_func(request, *args, **kwargs)

    return decorator
