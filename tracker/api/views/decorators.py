from functools import wraps

from django.views.decorators.cache import cache_page


def cache_page_for_public(*cache_args, **cache_kwargs):
    def inner(func):
        @wraps(func)
        def inner_method(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return cache_page(*cache_args, *cache_kwargs)(func)(
                    request, *args, **kwargs
                )
            return func(request, *args, **kwargs)

        return inner_method

    return inner
