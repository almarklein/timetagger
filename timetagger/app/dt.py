"""
PScript implementation of datetime utilities.
"""

from pscript import this_is_js, RawJS
from pscript.stubs import Date, isNaN, Math, window


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


_start_time = now()


def time_since_app_loaded():
    """Get the number of seconds since the app loaded."""
    return now() - _start_time


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
    return max(int(t), 0)  # for dates before the epoch (1970) just clip


def get_timezone_indicator(t, sep="", utc_offset=None):
    PSCRIPT_OVERLOAD = False  # noqa
    if utc_offset is None:
        utc_offset = -(Date(t * 1000).getTimezoneOffset() / 60)
    sign = "+" if utc_offset >= 0 else "-"
    utc_offset_unsigned = Math.abs(utc_offset)
    h = Math.floor(utc_offset_unsigned)
    m = utc_offset_unsigned - h
    h, m = str(h), str(Math.floor(m * 60))
    if len(m) == 1:
        m = "0" + m
    if len(h) == 1:
        h = "0" + h
    return sign + h + sep + m


def time2str(t, utc_offset=None):
    """Convert a time int into a textual representation. If utc_offset is None, the
    representation is in local time. Otherwise the given offset (in hours) is
    used. Use utc_offset=0 for UTC. In all cases the zone is explicit in the result.
    """
    PSCRIPT_OVERLOAD = False  # noqa
    t = to_time_int(t)
    if this_is_js():  # pragma: no cover
        if utc_offset is None:
            utc_offset = -(Date(t * 1000).getTimezoneOffset() / 60)
        t += utc_offset * 3600
        s = Date(t * 1000).toISOString()
        s = s.split(".")[0]
        if utc_offset == 0:
            s += "Z"
        else:
            s += get_timezone_indicator(t, "", utc_offset)
    else:  # py
        import datetime

        if utc_offset is None:
            utc_offset = (
                datetime.datetime.fromtimestamp(t)
                - datetime.datetime.utcfromtimestamp(t)
            ).total_seconds() / 3600
        tz = datetime.timezone(datetime.timedelta(hours=utc_offset))
        dt = datetime.datetime.fromtimestamp(t, tz)
        if utc_offset == 0:
            s = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            s = dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    return s


def time2localstr(t):
    """Convert a time int into a textual local representation, and with a space instead of T. Note that the date is always yyyy-mm-dd"""
    s = time2str(t)
    s1, s2 = s.split("T")
    s2 = s2.split("-")[0].split("+")[0].rstrip("Z")
    return s1 + " " + s2


def format_isodate(date, fmt=None):
    "Format an iso date to a formatted date."
    yyyy, mm, dd = date.split("-")
    if fmt is None:
        fmt = "dd-mm-yyyy"
        if window.simplesettings:
            fmt = window.simplesettings.get("date_repr", fmt)
    if fmt == "yyyy-mm-dd":
        return yyyy + "-" + mm + "-" + dd
    elif fmt == "dd-mm-yyyy":
        return dd + "-" + mm + "-" + yyyy
    elif fmt == "mm/dd/yyyy":
        return mm + "/" + dd + "/" + yyyy
    else:
        return date


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
        day_offset = 7 - get_first_day_of_week()
        daysoff = (d.getDay() + day_offset) % 7  # Align to a sunday/monday
        tup = d.getFullYear(), d.getMonth(), (d.getDate() - daysoff)
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


def duration_string_colon(t, show_secs=False):
    PSCRIPT_OVERLOAD = False  # noqa
    # Note the floor-rounding for all but the last element
    sign = "-" if t < 0 else ""
    t = abs(t)
    if show_secs:
        part1 = f"{sign}{t//3600:.0f}:{(t//60)%60:02.0f}"
        part2 = f":{t%60:02.0f}"
        return (part1, part2) if show_secs == 2 else (part1 + part2)
    else:
        m = Math.round(t / 60)
        # Note how for anythinh below 30s is shown as 00:00. This is
        # intentional because a single 00:00:28 would stand out quite
        # oddly in a series of hh:mm entries.
        return f"{sign}{m//60:.0f}:{m%60:02.0f}"


def duration_string(t, show_secs=False, repr=None):
    PSCRIPT_OVERLOAD = False  # noqa
    if not repr:
        repr = "hms"
        if window.simplesettings:
            repr = window.simplesettings.get("duration_repr", "hms")
    if repr == "hms" or repr == "dhms":
        sign = "-" if t < 0 else ""
        t = abs(t)
        if show_secs:
            # Prep the numbers
            m = (t // 60) % 60
            h = t // 3600
            d = 0
            if repr == "dhms":
                d = h // 24
                h -= d * 24
            # Show hours and days only if they are nonzero
            if d:
                part1 = f"{sign}{d:.0f}d{h:02.0f}h{m:02.0f}m"
            elif h:
                part1 = f"{sign}{h:.0f}h{m:02.0f}m"
            else:
                part1 = f"{sign}{m:.0f}m"
            # Combine with seconds
            part2 = f"{t%60:02.0f}s"
            return (part1, part2) if show_secs == 2 else (part1 + part2)
        else:
            # Prep the numbers
            m = Math.round(t / 60)
            h = m // 60
            d = 0
            if repr == "dhms":
                d = h // 24
                h -= d * 24
            if d:
                return f"{sign}{d:.0f}d{h:02.0f}h{m%60:02.0f}m"
            elif h:
                return f"{sign}{h:.0f}h{m%60:02.0f}m"
            elif t >= 60:
                return f"{sign}{m%60:.0f}m"
            else:
                # Only show the secs (even if show_secs is False)
                return f"{sign}{t:.0f}s"

    else:
        return duration_string_colon(t, show_secs)


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
    return d.getDay() == get_first_day_of_week()  # 0: Sunday, 1: Monday


def get_first_day_of_week():
    PSCRIPT_OVERLOAD = False  # noqa
    if window.simplesettings:
        return window.simplesettings.get("first_day_of_week", 1)
    else:
        return 1


def get_weeknumber(t):
    """Get the ISO 8601 week number."""
    # From https://weeknumber.net/how-to/javascript
    date = Date(t * 1000)  # noqa
    day_offfset = 7 - get_first_day_of_week()  # noqa
    RawJS(
        """
    date.setHours(0, 0, 0, 0);
    // Thursday in current week decides the year.
    date.setDate(date.getDate() + 3 - (date.getDay() + day_offfset) % 7);
    // January 4 is always in week 1.
    var week1 = new Date(date.getFullYear(), 0, 4);
    // Adjust to Thursday in week 1 and count number of weeks from date to week1.
    var res = 1 + Math.round(((date.getTime() - week1.getTime()) / 86400000
                               - 3 + (week1.getDay() + 6) % 7) / 7);
    """
    )
    return res  # noqa


def get_remaining_hours_of_day(t):
    d = Date(t * 1000)
    return 24 - d.getHours() - d.getMinutes() / 60 - d.getSeconds() / 3600


def get_elapsed_hours_of_day(t):
    d = Date(t * 1000)
    return d.getHours() + d.getMinutes() / 60 + d.getSeconds() / 3600


def get_free_hours_in_range(t1, t2, free_days):
    free_hours = 0
    if free_days >= 1:
        d1 = Date(t1 * 1000)
        d2 = Date(t2 * 1000)
        hours_in_range = (t2 - t1) / 3600

        if hours_in_range > 24:  # scale > "1D"
            while d1 < d2:
                if d1.getDay() == 0:  # sunday
                    free_hours += 24
                elif d1.getDay() == 6 and free_days == 2:  # saturday
                    free_hours += 24
                d1.setDate(d1.getDate() + 1)  # next day
        else:  # scale <= "1D"
            # starts on sunday
            if d1.getDay() == 0 and d2.getDay() != 0:
                free_hours = get_remaining_hours_of_day(t1)
            # only sunday
            elif d1.getDay() == 0 and d2.getDay() == 0:
                free_hours = hours_in_range
            # ends on sunday
            elif d1.getDay() != 0 and d2.getDay() == 0 and free_days != 2:
                free_hours = get_elapsed_hours_of_day(t2)
            # starts on saturday
            elif d1.getDay() == 6 and free_days == 2:
                free_hours = hours_in_range
            # ends on saturday
            elif d1.getDay() != 6 and d2.getDay() == 6 and free_days == 2:
                free_hours = get_elapsed_hours_of_day(t2)

    return free_hours


if __name__ == "__main__":
    import pscript

    pscript.script2js(
        __file__,
        target=__file__[:-3] + ".js",
        namespace="datetime",
        module_type="simple",
    )
