"""
Report utility functions shared between production code and tests.

These functions are pure logic that don't depend on browser environment
(window, document, etc.), so they can be tested directly in Python.
"""

from pscript import this_is_js, RawJS
from pscript.stubs import window


def duration2str(seconds):
    """Convert duration in seconds to string format.
    
    This is a simplified version for use in report_utils.
    The actual dialogs.py uses a different implementation that
    depends on window.simplesettings.
    """
    PSCRIPT_OVERLOAD = False  # noqa
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        if this_is_js():
            RawJS("return String(hours) + ':' + (minutes >= 10 ? String(minutes) : '0' + String(minutes))")
        else:
            return f"{hours}:{minutes:02d}"
    if this_is_js():
        RawJS("return String(minutes) + 'm'")
    else:
        return f"{minutes}m"


def to_str(s):
    """Convert to string, returning empty string if None."""
    PSCRIPT_OVERLOAD = False  # noqa
    if s is None:
        return ""
    if this_is_js():
        RawJS("return String(s).replace(/[\t\r\n]/g, '')")
    else:
        return str(s).replace("\t", "").replace("\r", "").replace("\n", "")


def get_period_from_timestamp(t1, group_period, dt):
    """Get period string from timestamp based on grouping period.
    
    Args:
        t1: timestamp (int, seconds since epoch)
        group_period: "day", "week", "month", "quarter", "year", or "none"
        dt: datetime module (dt.py) with time2localstr, format_isodate, etc.
    
    Returns:
        tuple: (period_str, date_str)
        - period_str: the period string (e.g., "2026-04-22" for day, "Apr 2026" for month)
        - date_str: ISO date string for sorting (e.g., "2026-04-22")
    """
    PSCRIPT_OVERLOAD = False  # noqa
    
    date = dt.time2localstr(t1).split(" ")[0]
    year = int(date.split("-")[0])
    
    if group_period == "day":
        period = dt.format_isodate(date)
    elif group_period == "week":
        week = dt.get_weeknumber(t1)
        if this_is_js():
            RawJS("period = String(year) + 'W' + String(week)")
        else:
            period = f"{year}W{week}"
    elif group_period == "month":
        month = int(date.split("-")[1])
        period = dt.MONTHS_SHORT[month - 1]
        if this_is_js():
            RawJS("period = period + ' ' + String(year)")
        else:
            period = f"{period} {year}"
    elif group_period == "quarter":
        month = int(date.split("-")[1])
        q = "111222333444"[month - 1]
        if this_is_js():
            RawJS("period = String(year) + 'Q' + q")
        else:
            period = f"{year}Q{q}"
    elif group_period == "year":
        if this_is_js():
            RawJS("period = String(year)")
        else:
            period = f"{year}"
    else:
        period = date
    
    return period, date


def group_records_by_period(
    records, group_period, dt, group_list1=None
):
    """Group records by time period and calculate min_t1/max_t2.
    
    This is the core logic for time period grouping with time range calculation.
    
    Args:
        records: list of record objects (each with t1, t2, duration, etc.)
        group_period: "day", "week", "month", "quarter", "year", or "none"
        dt: datetime module (dt.py)
        group_list1: optional list of primary groups (for tagz/ds grouping)
            If None, all records are treated as one "hidden" group.
    
    Returns:
        list: groups sorted by sortkey, each group has:
            - title: group title
            - duration: total duration
            - records: list of records in this group
            - sortkey: for sorting
            - min_t1: earliest t1 (for period grouping)
            - max_t2: latest t2 (for period grouping)
    """
    PSCRIPT_OVERLOAD = False  # noqa
    
    if group_period == "none":
        if group_list1:
            return group_list1
        else:
            if this_is_js():
                total_duration = 0
                for i in range(len(records)):
                    total_duration += records[i].duration
                return [{"title": "hidden", "duration": total_duration, "records": records}]
            else:
                return [{"title": "hidden", "duration": sum(r["duration"] for r in records), "records": records}]
    
    groups = {}
    
    if group_list1:
        for group_index in range(len(group_list1)):
            if this_is_js():
                group_title = group_list1[group_index].title
                group_records = group_list1[group_index].records
            else:
                group_title = group_list1[group_index]["title"]
                group_records = group_list1[group_index]["records"]
            
            for record in group_records:
                if this_is_js():
                    period, date = get_period_from_timestamp(record.t1, group_period, dt)
                else:
                    period, date = get_period_from_timestamp(record["t1"], group_period, dt)
                
                if group_title == "hidden":
                    title = period
                    sortkey = date
                else:
                    if this_is_js():
                        RawJS("title = period + ' / ' + group_title")
                        RawJS("sortkey = date + String(1000000 + group_index)")
                    else:
                        title = f"{period} / {group_title}"
                        sortkey = f"{date}{1000000 + group_index}"
                
                if title not in groups:
                    groups[title] = {
                        "title": title,
                        "duration": 0,
                        "records": [],
                        "sortkey": sortkey,
                        "min_t1": None,
                        "max_t2": None,
                    }
                
                g = groups[title]
                if this_is_js():
                    g.records.push(record)
                    g.duration += record.duration
                    if g.min_t1 is None or record.t1 < g.min_t1:
                        g.min_t1 = record.t1
                    if g.max_t2 is None or record.t2 > g.max_t2:
                        g.max_t2 = record.t2
                else:
                    g["records"].append(record)
                    g["duration"] += record["duration"]
                    if g["min_t1"] is None or record["t1"] < g["min_t1"]:
                        g["min_t1"] = record["t1"]
                    if g["max_t2"] is None or record["t2"] > g["max_t2"]:
                        g["max_t2"] = record["t2"]
    else:
        for record in records:
            if this_is_js():
                period, date = get_period_from_timestamp(record.t1, group_period, dt)
            else:
                period, date = get_period_from_timestamp(record["t1"], group_period, dt)
            title = period
            sortkey = date
            
            if title not in groups:
                groups[title] = {
                    "title": title,
                    "duration": 0,
                    "records": [],
                    "sortkey": sortkey,
                    "min_t1": None,
                    "max_t2": None,
                }
            
            g = groups[title]
            if this_is_js():
                g.records.push(record)
                g.duration += record.duration
                if g.min_t1 is None or record.t1 < g.min_t1:
                    g.min_t1 = record.t1
                if g.max_t2 is None or record.t2 > g.max_t2:
                    g.max_t2 = record.t2
            else:
                g["records"].append(record)
                g["duration"] += record["duration"]
                if g["min_t1"] is None or record["t1"] < g["min_t1"]:
                    g["min_t1"] = record["t1"]
                if g["max_t2"] is None or record["t2"] > g["max_t2"]:
                    g["max_t2"] = record["t2"]
    
    group_list = list(groups.values()) if not this_is_js() else list(groups.values())
    if this_is_js():
        group_list.sort(lambda a, b: a.sortkey.localeCompare(b.sortkey))
    else:
        group_list.sort(key=lambda x: x["sortkey"])
    
    return group_list


def calculate_time_range_from_group(group, dt):
    """Calculate formatted start and end time from a group.
    
    Args:
        group: group object with min_t1 and max_t2
        dt: datetime module
    
    Returns:
        tuple: (start_time_str, end_time_str)
        - Empty strings if min_t1 or max_t2 is None
        - Formatted as "HH:MM" if available
    """
    PSCRIPT_OVERLOAD = False  # noqa
    
    start_time = ""
    end_time = ""
    
    if this_is_js():
        min_t1 = group.min_t1
        max_t2 = group.max_t2
    else:
        min_t1 = group.get("min_t1")
        max_t2 = group.get("max_t2")
    
    if min_t1 is not None and max_t2 is not None:
        if this_is_js():
            parts1 = dt.time2localstr(min_t1).split(" ")
            parts2 = dt.time2localstr(max_t2).split(" ")
            st1 = parts1[1]
            st2 = parts2[1]
            st1 = st1.slice(0, -3)
            st2 = st2.slice(0, -3)
        else:
            parts1 = dt.time2localstr(min_t1).split(" ")
            parts2 = dt.time2localstr(max_t2).split(" ")
            st1 = parts1[1][:-3]
            st2 = parts2[1][:-3]
        
        start_time = st1
        end_time = st2
    
    return start_time, end_time


# ============================================================================
# CSV Export Functions
# ============================================================================

CSV_HEADER = "subtotals,tag_groups,duration,date,start,stop,description,user,tags,group_start,group_end"


def _escape_csv_ds(ds):
    """Escape description for CSV - helper function.
    
    Args:
        ds: description string
    
    Returns:
        str: quoted string with double quotes escaped
    """
    PSCRIPT_OVERLOAD = False  # noqa
    if this_is_js():
        RawJS("""return '"' + ds.replace(/"/g, '""') + '"'""")
    else:
        return '"' + ds.replace('"', '""') + '"'


def format_csv_row(row, user=""):
    """Format a single row for CSV export.
    
    This matches the logic in dialogs.py's _save_as_csv method.
    
    Column order (11 columns total):
    0: subtotals (for head rows: duration, for record rows: empty)
    1: tag_groups (for head rows: title, for record rows: empty)
    2: duration (for record rows only)
    3: date (for record rows only)
    4: start (for record rows only)
    5: stop (for record rows only)
    6: description (for record rows only, quoted)
    7: user
    8: tags (for record rows only)
    9: group_start (NEW: for head rows with time range)
    10: group_end (NEW: for head rows with time range)
    
    Args:
        row: row data (list)
        user: username string
    
    Returns:
        str: CSV formatted line
    """
    PSCRIPT_OVERLOAD = False  # noqa
    
    if row[0] == "blank":
        return ",,,,,,,,,,"
    elif row[0] == "head":
        start_time = row[4] if len(row) > 4 else ""
        end_time = row[5] if len(row) > 5 else ""
        if this_is_js():
            RawJS("return row[1] + ',' + row[2] + ',,,,,,,,,' + start_time + ',' + end_time")
        else:
            return f"{row[1]},{row[2]},,,,,,,,{start_time},{end_time}"
    elif row[0] == "record":
        duration = row[2]
        sd1 = row[3]
        st1 = row[4]
        st2 = row[5]
        ds = row[6]
        tagz = row[7]
        ds_escaped = _escape_csv_ds(ds)
        if this_is_js():
            RawJS("return ',,' + duration + ',' + sd1 + ',' + st1 + ',' + st2 + ',' + ds_escaped + ',' + user + ',' + tagz + ',,')
        else:
            return f",,{duration},{sd1},{st1},{st2},{ds_escaped},{user},{tagz},,"
    return ""


# ============================================================================
# Display Logic (HTML/PDF)
# ============================================================================

def should_show_time_range(row):
    """Determine if time range should be shown for a row.
    
    This is the core logic used by both HTML and PDF exports.
    
    Args:
        row: row data (list)
    
    Returns:
        tuple: (should_show, start_time, end_time)
    """
    PSCRIPT_OVERLOAD = False  # noqa
    
    start_time = row[4] if len(row) > 4 else ""
    end_time = row[5] if len(row) > 5 else ""
    
    should_show = bool(start_time and end_time)
    
    return should_show, start_time, end_time


def format_html_time_range(row):
    """Format time range for HTML display.
    
    Matches the logic in _generate_table_html.
    
    Args:
        row: row data
    
    Returns:
        str: HTML span for time range, or empty string
    """
    PSCRIPT_OVERLOAD = False  # noqa
    
    should_show, start_time, end_time = should_show_time_range(row)
    
    if should_show:
        if this_is_js():
            RawJS("return '<span style=\"font-size:0.85em;color:#666;margin-left:1em;\">' + start_time + ' - ' + end_time + '</span>'")
        else:
            return f"<span style='font-size:0.85em;color:#666;margin-left:1em;'>{start_time} - {end_time}</span>"
    
    return ""


def format_pdf_time_range(row):
    """Format time range for PDF display.
    
    Matches the logic in _save_as_pdf.
    
    Args:
        row: row data
    
    Returns:
        tuple: (should_show, time_range_text)
        - should_show: boolean
        - time_range_text: formatted text like "  09:00 - 17:00"
    """
    PSCRIPT_OVERLOAD = False  # noqa
    
    should_show, start_time, end_time = should_show_time_range(row)
    
    if should_show:
        if this_is_js():
            RawJS("return [true, '  ' + start_time + ' - ' + end_time]")
        else:
            return True, f"  {start_time} - {end_time}"
    
    return False, ""


# ============================================================================
# Row Generation Helper (for testing)
# ============================================================================

def generate_report_rows(
    records,
    group_method,
    group_period,
    showrecords,
    dt,
    name_map=None,
    priorities=None,
    user="",
):
    """Generate report rows from records.
    
    This is a simplified version of _generate_table_rows that can be tested
    directly. It doesn't depend on browser environment.
    
    Args:
        records: list of record dicts with: key, t1, t2, duration, tagz, ds
        group_method: "tagz", "ds", or "none"
        group_period: "day", "week", "month", "quarter", "year", or "none"
        showrecords: boolean, whether to include individual records
        dt: datetime module
        name_map: optional dict mapping tagz1 to tagz2 (for tag grouping)
        priorities: optional dict for tag priorities
        user: username for CSV export
    
    Returns:
        list: rows (each row is a list)
    """
    PSCRIPT_OVERLOAD = False  # noqa
    
    rows = []
    groups = {}
    group_list1 = []
    empty_title = "General"
    
    if name_map is None:
        name_map = {}
        for r in records:
            tagz = r.get("tagz", "")
            name_map[tagz] = tagz
    
    if group_method == "tagz":
        tagz_set = set()
        for r in records:
            tagz = r.get("tagz", "")
            if tagz in name_map:
                tagz_set.add(name_map[tagz])
        
        for tagz in tagz_set:
            groups[tagz] = {
                "title": tagz or empty_title,
                "duration": 0,
                "records": [],
            }
        
        for record in records:
            tagz1 = record.get("tagz", "")
            if tagz1 not in name_map:
                continue
            tagz2 = name_map[tagz1]
            group = groups[tagz2]
            group["records"].append(record)
            group["duration"] += record["duration"]
        
        group_list1 = list(groups.values())
    
    elif group_method == "ds":
        for record in records:
            tagz1 = record.get("tagz", "")
            if tagz1 not in name_map:
                continue
            ds = record.get("ds", "")
            if ds not in groups:
                groups[ds] = {"title": ds, "duration": 0, "records": []}
            group = groups[ds]
            group["records"].append(record)
            group["duration"] += record["duration"]
        
        group_list1 = list(groups.values())
        group_list1.sort(key=lambda x: x["title"].lower())
    
    else:
        group = {"title": "hidden", "duration": 0, "records": []}
        group_list1 = [group]
        for record in records:
            tagz1 = record.get("tagz", "")
            if name_map and tagz1 not in name_map:
                continue
            group["duration"] += record["duration"]
            group["records"].append(record)
    
    group_list2 = group_records_by_period(
        None, group_period, dt, group_list1
    )
    
    total_duration = 0
    for group in group_list2:
        if this_is_js():
            total_duration += group.duration
        else:
            total_duration += group["duration"]
    
    rows.append(["head", duration2str(total_duration), "Total", 0])
    
    for group in group_list2:
        if this_is_js():
            group_duration = duration2str(group.duration)
        else:
            group_duration = duration2str(group["duration"])
        pad = 1
        
        start_time, end_time = calculate_time_range_from_group(group, dt)
        
        if showrecords:
            rows.append(["blank"])
        
        if this_is_js():
            group_title = group.title
        else:
            group_title = group["title"]
        
        if group_title != "hidden":
            rows.append(["head", group_duration, group_title, pad, start_time, end_time])
        
        if showrecords:
            if this_is_js():
                for i in range(len(group.records)):
                    record = group.records[i]
                    sd1, st1 = dt.time2localstr(record.t1).split(" ")
                    sd2, st2 = dt.time2localstr(record.t2).split(" ")
                    st1 = st1.slice(0, -3)
                    st2 = st2.slice(0, -3)
                    rec_duration = duration2str(record.duration)
                    rows.append([
                        "record",
                        record.key,
                        rec_duration,
                        dt.format_isodate(sd1),
                        st1,
                        st2,
                        to_str(record.get("ds", "")),
                        record.get("tagz", ""),
                    ])
            else:
                for record in group["records"]:
                    sd1, st1 = dt.time2localstr(record["t1"]).split(" ")
                    sd2, st2 = dt.time2localstr(record["t2"]).split(" ")
                    st1 = st1[:-3]
                    st2 = st2[:-3]
                    rec_duration = duration2str(record["duration"])
                    rows.append([
                        "record",
                        record["key"],
                        rec_duration,
                        dt.format_isodate(sd1),
                        st1,
                        st2,
                        to_str(record.get("ds", "")),
                        record.get("tagz", ""),
                    ])
    
    return rows


if __name__ == "__main__":
    import pscript
    
    pscript.script2js(
        __file__,
        target=__file__[:-3] + ".js",
        namespace="report_utils",
        module_type="simple",
    )
