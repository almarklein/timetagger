"""
PScript implementation of datetime utilities.
"""

from pscript import this_is_js, RawJS
from pscript.stubs import Date, isNaN, Math


DAYS_SHORT = [
    "Sun",
    "Mon",
    "Tue",
    "Wed",
    "Thu",
    "Fri",
    "Sat",
]  # d.getdDay() zero is sunday
DAYS_LONG = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
]

MONTHS_SHORT = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]
MONTHS_LONG = [
    "Januari",
    "Februari",
    "March",
    "April",
    "May",
    "June",
    "Juli",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def now():
    """Get the current time in seconds, as a float."""
    if this_is_js():
        return Date().getTime() / 1000
    else:
        import time

        return time.time()


def to_time_int(t):
    """Get a time (in int seconds since epoch), given float/str input.
    String inputs can be:

    * 'now': get current time.
    * E.g. '2018-04-24 11:23:00' for a local time (except in Safari :/).
    * E.g. '2018-04-24 11:23:00Z' for a time in UTC.
    * E.g. '2018-04-24 11:23:00+0200' for AMS summertime in this case.

    In the above, one can use a 'T' instead of a space between data and time
    to comply with ISO 8601.
    """
    if this_is_js():
        if isinstance(t, Date):
            t = t.getTime() / 1000
    if isinstance(t, str):
        t = t.strip()
        if this_is_js():  # pragma: no cover
            if t.lower() == "now":
                t = Date().getTime() / 1000
            else:
                if t.count(" ") == 1 and t[10] == " ":
                    t = t.replace(" ", "T")  # Otherwise Safari wont take it
                t = Date(t).getTime() / 1000  # Let browser handle date parsing
        else:  # py
            import datetime

            t = t.replace("T", " ")
            if t.lower() == "now":
                t = datetime.datetime.now().timestamp()
            elif t.endswith("Z") or t[-5] in "-+":  # ISO 8601
                t = (t[:-1] + "+0000") if t.endswith("Z") else t
                t = datetime.datetime.strptime(t, "%Y-%m-%d %H:%M:%S%z").timestamp()
            else:
                t = datetime.datetime.strptime(t, "%Y-%m-%d %H:%M:%S").timestamp()
    if not isinstance(t, (int, float)):
        raise RuntimeError(f"Time must be a number, not {t!r}")
    return int(t)


def time2str(t, utc_offset=None):
    """Convert a time int into a textual representation. If utc_offset is None, the
    representation is in local time. Otherwise the given offset (in hours) is
    used. Use utc_offset=0 for UTC. In all cases the zone is explicit in the result.
    """
    t = to_time_int(t)
    if this_is_js():  # pragma: no cover
        if utc_offset is None:
            utc_offset = -(Date(t * 1000).getTimezoneOffset() // 60)
        t += utc_offset * 3600
        s = Date(t * 1000).toISOString()
        s = s.split(".")[0]
        if utc_offset == 0:
            s += "Z"
        else:
            s += f"{utc_offset:+03.0f}"
    else:  # py
        import datetime

        if utc_offset is None:
            utc_offset = (
                datetime.datetime.fromtimestamp(t)
                - datetime.datetime.utcfromtimestamp(t)
            ).total_seconds() // 3600
        tz = datetime.timezone(datetime.timedelta(hours=utc_offset))
        dt = datetime.datetime.fromtimestamp(t, tz)
        if utc_offset == 0:
            s = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            s = dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    return s


def time2localstr(t):
    """Convert a time int into a textual local representation, and with a space instead of T."""
    s = time2str(t)
    s1, s2 = s.split("T")
    s2 = s2.split("-")[0].split("+")[0].rstrip("Z")
    return s1 + " " + s2


def round(t, res):
    """Round the given date to the nearest resolution step."""
    PSCRIPT_OVERLOAD = False  # noqa
    dt = add(t, res) - t
    return floor(t + 0.5 * dt, res)


def floor(t, res):
    """Round the given date down to the nearest smaller resolution step."""
    PSCRIPT_OVERLOAD = False  # noqa

    resName = res[-1]
    resFactor = float(res[:-1])

    d = Date(t * 1000)
    tup = (
        d.getFullYear(),
        d.getMonth(),
        d.getDate(),
        d.getHours(),
        d.getMinutes(),
        d.getSeconds(),
    )
    if resName == "s":
        tup[-1] = int(tup[-1] / resFactor) * resFactor
    elif resName == "m":
        tup = tup[:5]
        tup[-1] = int(tup[-1] / resFactor) * resFactor
    elif resName == "h":
        tup = tup[:4]
        tup[-1] = int(tup[-1] / resFactor) * resFactor
    elif resName == "D":
        tup = tup[:3]
        tup[-1] = int((tup[-1] - 1) / resFactor) * resFactor + 1  # days are 1-based
    elif resName == "W":
        d.setHours(0, 0, 0, 0)
        daysoff = (d.getDay() + 6) % 7  # Align to a monday
        d = Date(d.getTime() - 86_400_000 * daysoff)
        tup = d.getFullYear(), d.getMonth(), d.getDate()
    elif resName == "M":
        tup = tup[:2]  # Note that it is zero-based (jan is zero)
        tup[-1] = int(tup[-1] / resFactor) * resFactor
        tup.extend([1])
    elif resName == "Y":
        tup = tup[:1]
        tup[-1] = int(tup[-1] / resFactor) * resFactor
        tup.extend([0, 1])
    else:
        raise RuntimeError("Invalid resolution: " + res)

    while len(tup) < 6:
        tup.append(0)
    return (
        Date(tup[0], tup[1], tup[2], tup[3], tup[4], tup[5]).getTime() / 1000
    )  # cant do *tup


def add(t, delta):
    """Add a delta to the given date. Delta can be an int (number of seconds),
    or a delta string like '4h', "21s", "2M" or "2Y". Works correctly for months
    and keeps leap years into account.
    """
    PSCRIPT_OVERLOAD = False  # noqa

    if isinstance(delta, (float, int)):
        delta = str(delta) + "s"

    deltaName = delta[-1]
    deltaFactor = float(delta[:-1])
    if isNaN(deltaFactor):
        raise RuntimeError(f"Cannot create delta from {delta!r}")

    d = Date(t * 1000)
    tup = (
        d.getFullYear(),
        d.getMonth(),
        d.getDate(),
        d.getHours(),
        d.getMinutes(),
        d.getSeconds(),
    )
    if deltaName == "s":
        tup[5] += deltaFactor
    elif deltaName == "m":
        tup[4] += deltaFactor
    elif deltaName == "h":
        tup[3] += deltaFactor
    elif deltaName == "D":
        tup[2] += deltaFactor
    elif deltaName == "W":
        tup[2] += deltaFactor * 7
    elif deltaName == "M":
        tup[1] += deltaFactor
    elif deltaName == "Y":
        tup[0] += deltaFactor
    else:
        raise RuntimeError("Invalid datetime delta: " + delta)

    return Date(tup[0], tup[1], tup[2], tup[3], tup[4], tup[5]).getTime() / 1000


def duration_string(t, show_secs=False):
    # Note the floor-rounding for all but the last element
    if show_secs:
        # return f"{t//3600:.0f}h{(t//60)%60:.0f}m{t%60:.0f}s"
        return f"{t//3600:.0f}:{(t//60)%60:02.0f}:{t%60:02.0f}"
    else:
        m = Math.round(t / 60)
        # return f"{m//60:.0f}h{m%60:.0f}m"
        return f"{m//60:.0f}:{m%60:02.0f}"


# %% Functions to query time props


def get_year_month_day(t):
    if this_is_js():
        d = Date(t * 1000)
        return d.getFullYear(), d.getMonth() + 1, d.getDate()
    else:
        import datetime

        dt = datetime.datetime.fromtimestamp(t)
        return dt.year, dt.month, dt.day


def get_month_shortname(t):
    d = Date(t * 1000)
    return MONTHS_SHORT[d.getMonth()]


def get_weekday_shortname(t):
    d = Date(t * 1000)
    return DAYS_SHORT[d.getDay()]  # getDay starts at zero, which represents Sunday


def get_weekday_longname(t):
    d = Date(t * 1000)
    return DAYS_LONG[d.getDay()]


def is_first_day_of_week(t):
    d = Date(t * 1000)
    return d.getDay() == 1  # Monday


def get_weeknumber(t):
    """Get the ISO 8601 week number."""
    # From https://weeknumber.net/how-to/javascript
    date = Date(t * 1000)  # noqa
    RawJS(
        """
    date.setHours(0, 0, 0, 0);
    // Thursday in current week decides the year.
    date.setDate(date.getDate() + 3 - (date.getDay() + 6) % 7);
    // January 4 is always in week 1.
    var week1 = new Date(date.getFullYear(), 0, 4);
    // Adjust to Thursday in week 1 and count number of weeks from date to week1.
    var res = 1 + Math.round(((date.getTime() - week1.getTime()) / 86400000
                               - 3 + (week1.getDay() + 6) % 7) / 7);
    """
    )
    return res  # noqa


def get_timezone_info(t):
    d = Date(t * 1000)
    d_winter = Date(d.getFullYear(), 0, 1)
    d_summer = Date(d.getFullYear(), 6, 1)
    #
    offset = -d.getTimezoneOffset() / 60
    offset_winter = -d_winter.getTimezoneOffset() / 60
    offset_summer = -d_summer.getTimezoneOffset() / 60
    return offset, offset_winter, offset_summer


if __name__ == "__main__":
    import pscript

    pscript.script2js(
        __file__,
        target=__file__[:-3] + ".js",
        namespace="datetime",
        module_type="simple",
    )
