from datetime import datetime

from rest_framework.exceptions import ParseError

from tracker.api import messages


def parse_time(time: None | str | int | datetime) -> datetime:
    """api helper to throw the correct exception"""
    from tracker.util import parse_time

    try:
        return parse_time(time)
    except (TypeError, ValueError):
        raise ParseError(
            detail=messages.INVALID_TIMESTAMP, code=messages.INVALID_TIMESTAMP_CODE
        )
