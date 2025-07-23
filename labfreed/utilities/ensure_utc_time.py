from datetime import datetime, timezone


def ensure_utc(dt: datetime) -> datetime:
    '''Converts to UTC time. If dt has no timezone it is assumed to be in UTC and the utc timezone is explicitly added'''
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)