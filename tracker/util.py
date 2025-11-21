"""
A collection of some generic useful methods

IMPORTANT: do not import anything other than standard libraries here, this should be usable by _everywhere_ if possible.
Specifically, do not include anything django or tracker specific in the top level imports, so that we
can use it in migrations, or inside the `model` files
"""

import collections.abc
import datetime
import itertools
import os
import random
import re
import secrets
import sys
import urllib.parse
from typing import Iterable, Optional, Sized


def natural_list_parse(s, symbol_only=False):
    """Parses a 'natural language' list, e.g.. seperated by commas,
    semi-colons, 'and', 'or', etc..."""
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
    return [x for x in [x.strip() for x in tokens] if len(x) > 0]


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
    import zoneinfo

    """This is a trick used by academic conference submission deadlines
    to use the last possible timezone to define the end of a particular date"""
    return zoneinfo.ZoneInfo('Etc/GMT-12')


def make_rand(rand_source=None, rand_seed=None):
    if rand_source is None:
        if rand_seed is None:
            rand_source = random.SystemRandom()
        else:
            rand_source = random.Random(rand_seed)
    return rand_source


def make_auth_code(length=64):
    """returns a securely generated hex string"""
    assert length % 2 == 0
    return secrets.token_hex(length // 2)


def random_num_replace(s, replacements, max_length=None):
    """Attempts to 'uniquify' a string by adding/replacing characters with a hex string
    of the specified length"""
    if max_length is None:
        max_length = len(s) + replacements
    if max_length < replacements:
        raise Exception(
            'Error, max_length ({0}) was less than the number of requested replacements ({1})'.format(
                max_length, replacements
            )
        )
    originalLength = len(s)
    endReplacements = min(max_length - len(s), replacements)
    s += make_auth_code(endReplacements)
    if endReplacements < replacements:
        replacementsLeft = replacements - endReplacements
        s = (
            s[: originalLength - replacementsLeft]
            + make_auth_code(replacementsLeft)
            + s[originalLength:]
        )
    return s


def median(queryset, column, *, count=None):
    count = count or queryset.count()
    if count == 0:
        return 0
    elif count % 2 == 0:
        return (
            sum(
                o[column]
                for o in queryset.order_by(column).values(column)[
                    count // 2 - 1 : count // 2 + 1
                ]
            )
            / 2
        )
    else:
        return queryset.order_by(column).values(column)[count // 2][column]


def flatten(iterable):
    """
    taking a collection of possibly nested iterables, returns a generator that
    yields them as one flat stream, order is only guaranteed if the underlying
    iterables guarantee order, strings are not counted as iterables and are returned
    as is
    """
    if isinstance(iterable, str) or not isinstance(iterable, collections.abc.Iterable):
        yield iterable
    else:
        yield from itertools.chain(*(flatten(el) for el in iterable))


def flatten_dict(d):
    """
    similar to flatten, except it operates on the values in a dict, ordering is only guaranteed
    if the underlying dict (and all subvalues) guarantees ordering
    """
    # TODO: if we hit a non-dict, we start iterating over subvalue keys instead if we end up back in a dict,
    #  but so far we haven't run into that use case
    for k, v in d.items():
        if isinstance(v, dict):
            yield from flatten_dict(v)
        else:
            yield from flatten(v)


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def set_mismatch(expected, actual):
    return set(expected) - set(actual), set(actual) - set(expected)


def parse_time(time: None | str | int | datetime.datetime) -> datetime.datetime:
    """
    None = 'now'
    str = if digits only, parse as unix timestamp, else try to parse as iso timestamp
    int = parse as unix timestamp
    datetime = return as is
    """
    if time is None:
        return utcnow()
    elif isinstance(time, datetime.datetime):
        return time
    elif isinstance(time, str):
        if re.match(r'^\d+$', time):
            return parse_time(int(time))
        else:
            # TODO: remove this when 3.11 is oldest supported version
            if sys.version_info < (3, 11):
                import dateutil.parser

                return dateutil.parser.parse(time)
            else:
                return datetime.datetime.fromisoformat(time)
    elif isinstance(time, int):
        return datetime.datetime.fromtimestamp(time, tz=datetime.timezone.utc)
    else:
        raise TypeError(
            f'argument must be None, int, str, or datetime, got {type(time)}'
        )


def get_public_site_prefix(url: Optional[str] = None, request=None) -> str:
    """
    returns either the domain for TRACKER_PUBLIC_SITE_ID/SITE_ID, or extracts the domain from the provided URL.
    Includes the scheme if one is provided, or a scheme-relative prepended URL if not.

    e.g.

    - `one.com/foo` returns `//one.com`
    - `//two.com/foo` returns `//two.com`
    - `https://three.com/foo` returns `https://three.com`

    :param url: a string representing a domain to use, or a url that can be parsed as such
    :param request: an HttpRequest instance, will be used as a fallback if url is not provided and Sites support is
      not active
    :return: see above
    """
    from django.apps import apps
    from django.contrib.sites.models import Site

    from tracker import settings

    if not url:
        if apps.is_installed('django.contrib.sites'):
            site_id = settings.TRACKER_PUBLIC_SITE_ID or settings.SITE_ID
            url = Site.objects.get(id=site_id).domain
        elif request:
            url = request.get_full_path()
        else:
            raise ValueError(
                'must provide a fallback value if the Sites framework is not configured and no request is passed.'
            )

    if (parsed := urllib.parse.urlparse(url)).netloc == '':
        parsed = urllib.parse.urlparse(f'//{url}')

    if parsed.scheme:
        domain = f'{parsed.scheme}://{parsed.netloc}'
    else:
        domain = f'//{parsed.netloc}'

    return domain


def build_public_url(url: str, request=None):
    """
    allows requests from a given site to override the domain for generated URLs to use a specific
    site, e.g. for sending out prize winner notifications from a private domain that point to the
    public one. If not set, will attempt to fall back on the provided request, if there is one.

    See `TRACKER_PUBLIC_SITE_ID` for more details.
    """
    from tracker import settings

    if settings.TRACKER_PUBLIC_SITE_ID is None:
        if request:
            return request.build_absolute_uri(url)
        else:
            return url
    else:
        domain = get_public_site_prefix()
        if request:
            return urllib.parse.urljoin(
                urllib.parse.urljoin(f'{request.scheme}://', domain), url
            )
        else:
            return urllib.parse.urljoin(domain, url)


def ellipsify(s: str, n: int) -> str:
    if len(s) > n:
        return s[: n - 3] + '...'
    else:
        return s


def tqdm_groupby(iterable: Iterable, *args, key, **kwargs):
    """
    attempts to provide a sensible tqdm bar when using groupby, if the passed in iterable is sized
    it will use that information for the completion estimate, and updates the bar every time a group
    is processed

    if tqdm is not installed, it acts as a simple passthrough
    """
    from itertools import groupby

    if not os.environ.get('TRACKER_DISABLE_TQDM', ''):
        try:
            from tqdm import tqdm

            total = len(iterable) if isinstance(iterable, Sized) else None
            with tqdm(iterable, *args, total=total, **kwargs) as t:
                for k, g in groupby(iterable, key):
                    g = list(g)
                    yield k, (i for i in g)
                    if total is not None:
                        t.update(len(g))
        except ImportError:
            pass

    else:
        yield from groupby(iterable, key)
