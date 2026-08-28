import datetime as dt
from zoneinfo import ZoneInfo


def localnow() -> dt.datetime:
    return dt.datetime.now(ZoneInfo("Asia/Almaty"))
