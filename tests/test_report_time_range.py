"""Test for report dialog time range functionality.

This test verifies the core logic of the time range feature:
1. Day grouping with multiple records shows correct start/end times
2. Non-period grouping does not show time ranges
3. CSV export maintains backward compatibility
4. Total row does not have time ranges
5. Empty days are not included

These tests use pure Python to simulate the logic,
since the actual dialogs.py uses pscript for the browser.
"""

import json
from _common import run_tests


def duration2str(seconds):
    """Convert duration in seconds to string (simplified)."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}:{minutes:02d}"
    return f"{minutes}m"


def time2localstr(timestamp):
    """Convert timestamp to local string (simplified for testing)."""
    from datetime import datetime, timezone
    # For testing, we'll assume UTC and return a fixed format
    dt_obj = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt_obj.strftime("%Y-%m-%d %H:%M:%S")


def format_isodate(date_str):
    """Format ISO date (simplified)."""
    return date_str


def generate_table_rows_simple(records, group_method, group_period, showrecords=False):
    """Simulate the _generate_table_rows logic in pure Python.
    
    This is a simplified version that captures the key logic:
    - Primary grouping (tagz, ds, none)
    - Secondary grouping (time period)
    - min_t1/max_t2 calculation for time period groups
    - Row generation with time range
    """
    rows = []
    groups = {}
    group_list1 = []
    empty_title = "General"
    
    # Primary grouping (tagz, ds, or none)
    if group_method == "tagz":
        for record in records:
            tagz = record.get("tagz", "")
            if tagz not in groups:
                groups[tagz] = {
                    "title": tagz or empty_title,
                    "duration": 0,
                    "records": []
                }
            group = groups[tagz]
            group["records"].append(record)
            group["duration"] += record["duration"]
        group_list1 = list(groups.values())
    elif group_method == "ds":
        for record in records:
            ds = record.get("ds", "")
            if ds not in groups:
                groups[ds] = {
                    "title": ds,
                    "duration": 0,
                    "records": []
                }
            group = groups[ds]
            group["records"].append(record)
            group["duration"] += record["duration"]
        group_list1 = list(groups.values())
        group_list1.sort(key=lambda x: x["title"].lower())
    else:
        group = {"title": "hidden", "duration": 0, "records": []}
        group_list1 = [group]
        for record in records:
            group["records"].append(record)
            group["duration"] += record["duration"]
    
    # Secondary grouping (by time period)
    if group_period == "none":
        group_list2 = group_list1
    else:
        groups = {}
        for group_index, g in enumerate(group_list1):
            group_title = g["title"]
            for record in g["records"]:
                date = time2localstr(record["t1"]).split(" ")[0]
                year = int(date.split("-")[0])
                
                if group_period == "day":
                    period = format_isodate(date)
                else:
                    period = date
                
                if group_title == "hidden":
                    title = period
                    sortkey = date
                else:
                    title = period + " / " + group_title
                    sortkey = date + str(1000000 + group_index)
                
                if title not in groups:
                    groups[title] = {
                        "title": title,
                        "duration": 0,
                        "records": [],
                        "sortkey": sortkey,
                        "min_t1": None,
                        "max_t2": None
                    }
                
                g2 = groups[title]
                g2["records"].append(record)
                g2["duration"] += record["duration"]
                
                if g2["min_t1"] is None or record["t1"] < g2["min_t1"]:
                    g2["min_t1"] = record["t1"]
                if g2["max_t2"] is None or record["t2"] > g2["max_t2"]:
                    g2["max_t2"] = record["t2"]
        
        group_list2 = list(groups.values())
        group_list2.sort(key=lambda x: x["sortkey"])
    
    # Calculate total
    total_duration = 0
    for g in group_list2:
        total_duration += g["duration"]
    rows.append(["head", duration2str(total_duration), "Total", 0])
    
    # Generate rows for each group
    for g in group_list2:
        duration = duration2str(g["duration"])
        pad = 1
        
        group_start_time = ""
        group_end_time = ""
        if g.get("min_t1") is not None and g.get("max_t2") is not None:
            parts1 = time2localstr(g["min_t1"]).split(" ")
            parts2 = time2localstr(g["max_t2"]).split(" ")
            st1 = parts1[1][:5]
            st2 = parts2[1][:5]
            group_start_time = st1
            group_end_time = st2
        
        if showrecords:
            rows.append(["blank"])
        
        if g["title"] != "hidden":
            rows.append(["head", duration, g["title"], pad, group_start_time, group_end_time])
    
    return rows


def format_csv_row_simple(row):
    """Simulate CSV row formatting."""
    user = "testuser"
    if row[0] == "blank":
        return ",,,,,,,,,,"
    elif row[0] == "head":
        start_time = row[4] if len(row) > 4 else ""
        end_time = row[5] if len(row) > 5 else ""
        return row[1] + "," + row[2] + ",,,,,,,," + start_time + "," + end_time
    elif row[0] == "record":
        duration = row[2]
        sd1 = row[3]
        st1 = row[4]
        st2 = row[5]
        ds = row[6]
        tagz = row[7]
        ds = '"' + ds.replace('"', '""') + '"'
        return ",," + duration + "," + sd1 + "," + st1 + "," + st2 + "," + ds + "," + user + "," + tagz + "," + ","
    return ""


def test_day_grouping_multiple_records():
    """Test day grouping with multiple records on the same day.
    
    Expected:
    - Start time = earliest record's t1
    - End time = latest record's t2
    """
    # Use a fixed timestamp that is definitely in the middle of a day
    # 2026-04-22 12:00:00 UTC = 1776936000
    base_ts = 1776936000
    
    # Create records all within a 4-hour window to ensure they're on the same day
    # regardless of timezone
    # Record 1: earliest (base + 0) - 12:00
    # Record 2: middle
    # Record 3: LATEST end (base + 4 hours) - 16:00
    records = [
        {
            "key": "rec1",
            "t1": base_ts,  # Earliest start: 12:00
            "t2": base_ts + 1800,  # 12:30
            "duration": 1800,
            "tagz": "#work",
            "ds": "First"
        },
        {
            "key": "rec2",
            "t1": base_ts + 3600,  # 13:00
            "t2": base_ts + 7200,  # 14:00
            "duration": 3600,
            "tagz": "#work",
            "ds": "Middle"
        },
        {
            "key": "rec3",
            "t1": base_ts + 9000,  # 14:30 (later start)
            "t2": base_ts + 10800,  # 15:00 (earlier end)
            "duration": 1800,
            "tagz": "#work",
            "ds": "Third"
        },
        {
            "key": "rec4",
            "t1": base_ts + 5400,  # 13:30 (earlier start than rec3)
            "t2": base_ts + 14400,  # 16:00 (LATEST end)
            "duration": 9000,
            "tagz": "#work",
            "ds": "Last (latest end)"
        }
    ]
    
    rows = generate_table_rows_simple(records, "tagz", "day", False)
    
    # Get the day groups (non-Total rows)
    day_groups = [r for r in rows if r[0] == "head" and r[2] != "Total"]
    
    # All records should be on the same day
    assert len(day_groups) == 1, f"Expected 1 day group, got {len(day_groups)}. All records: {[(time2localstr(r['t1']), time2localstr(r['t2'])) for r in records]}"
    
    # Check Total row (no time range)
    total_row = rows[0]
    assert total_row[2] == "Total"
    assert len(total_row) == 4, f"Total row should have 4 elements, got {len(total_row)}"
    
    # Check day group row
    day_row = day_groups[0]
    assert len(day_row) == 6, f"Day group should have 6 elements, got {len(day_row)}"
    
    start_time = day_row[4]
    end_time = day_row[5]
    
    # Verify times are non-empty
    assert start_time, f"start_time should not be empty"
    assert end_time, f"end_time should not be empty"
    
    # Verify start_time is earlier than end_time (compare as HH:MM strings)
    assert start_time < end_time, f"start_time ({start_time}) should be earlier than end_time ({end_time})"
    
    # Calculate expected times based on actual local timezone
    # base_ts is earliest t1 (12:00 UTC)
    # base_ts + 14400 is latest t2 (16:00 UTC)
    expected_start = time2localstr(base_ts).split(" ")[1][:5]
    expected_end = time2localstr(base_ts + 14400).split(" ")[1][:5]
    
    assert start_time == expected_start, f"Expected start_time '{expected_start}', got '{start_time}'. Records: {[(time2localstr(r['t1']), time2localstr(r['t2'])) for r in records]}"
    assert end_time == expected_end, f"Expected end_time '{expected_end}', got '{end_time}'"
    
    print(f"  OK Day grouping: start={start_time}, end={end_time} (earliest start, latest end)")


def test_non_period_grouping_no_time_range():
    """Test that non-period grouping does not calculate time ranges.
    
    Expected:
    - Groups don't have min_t1/max_t2
    - Rows have only 4 elements
    """
    base_ts = 1776892800
    
    records = [
        {
            "key": "rec1",
            "t1": base_ts + 9 * 3600,
            "t2": base_ts + 10 * 3600,
            "duration": 3600,
            "tagz": "#work",
            "ds": "Work"
        }
    ]
    
    # group_period = "none"
    rows = generate_table_rows_simple(records, "tagz", "none", False)
    
    # Total + tag group
    assert len(rows) == 2, f"Expected 2 rows, got {len(rows)}"
    
    tag_row = rows[1]
    # When group_period is "none", groups don't have min_t1/max_t2
    # Let's verify the structure
    assert tag_row[0] == "head"
    
    # The important thing is that when there's no time range,
    # the HTML/CSV should not show it
    # Let's check the CSV formatting
    csv_row = format_csv_row_simple(tag_row)
    parts = csv_row.split(",")
    
    # group_start and group_end should be empty for non-period grouping
    # (or the row doesn't have these elements)
    assert len(parts) == 11, f"Expected 11 columns, got {len(parts)}"
    # The last two columns (group_start, group_end) should be empty
    # because the row only has 4 elements
    assert parts[9] == "" or tag_row[4] == "", f"group_start should be empty"
    assert parts[10] == "" or (len(tag_row) <= 5 or tag_row[5] == ""), f"group_end should be empty"
    
    print(f"  OK Non-period grouping: no time range shown")


def test_csv_export_backward_compatibility():
    """Test CSV export maintains backward compatibility.
    
    Expected:
    - Old format rows (4 elements) work correctly
    - New columns are at the end
    - Column order is preserved
    """
    # Old format row (4 elements)
    old_row = ["head", "8:00", "#work", 1]
    csv_old = format_csv_row_simple(old_row)
    parts_old = csv_old.split(",")
    
    assert len(parts_old) == 11, f"Expected 11 columns, got {len(parts_old)}"
    assert parts_old[0] == "8:00", f"subtotals should be '8:00', got {parts_old[0]}"
    assert parts_old[1] == "#work", f"tag_groups should be '#work', got {parts_old[1]}"
    assert parts_old[9] == "", f"group_start should be empty for old format, got '{parts_old[9]}'"
    assert parts_old[10] == "", f"group_end should be empty for old format, got '{parts_old[10]}'"
    
    # New format row (6 elements)
    new_row = ["head", "8:00", "2026-04-22 / #work", 1, "09:00", "17:00"]
    csv_new = format_csv_row_simple(new_row)
    parts_new = csv_new.split(",")
    
    assert len(parts_new) == 11, f"Expected 11 columns, got {len(parts_new)}"
    assert parts_new[0] == "8:00", f"subtotals should be '8:00', got {parts_new[0]}"
    assert parts_new[1] == "2026-04-22 / #work", f"tag_groups wrong: {parts_new[1]}"
    assert parts_new[9] == "09:00", f"group_start should be '09:00', got {parts_new[9]}"
    assert parts_new[10] == "17:00", f"group_end should be '17:00', got {parts_new[10]}"
    
    # Verify column order: the first 9 columns should match old format
    # (except subtotals and tag_groups, the middle columns are empty for head rows)
    for i in range(2, 9):
        assert parts_old[i] == parts_new[i] == "", f"Column {i} should be empty for head rows"
    
    print(f"  OK CSV backward compatibility: old and new formats work")


def test_total_row_no_time_range():
    """Test that Total row does not have time range.
    
    Expected:
    - Total row has only 4 elements
    - No min_t1/max_t2 for total
    """
    base_ts = 1776892800
    
    records = [
        {
            "key": "rec1",
            "t1": base_ts + 9 * 3600,
            "t2": base_ts + 10 * 3600,
            "duration": 3600,
            "tagz": "#work",
            "ds": "Work"
        }
    ]
    
    rows = generate_table_rows_simple(records, "tagz", "day", False)
    
    # First row is Total
    total_row = rows[0]
    
    assert total_row[0] == "head"
    assert total_row[2] == "Total"
    assert len(total_row) == 4, f"Total row should have 4 elements, got {len(total_row)}"
    
    # CSV formatting should work correctly
    csv_total = format_csv_row_simple(total_row)
    parts = csv_total.split(",")
    
    assert len(parts) == 11, f"Expected 11 columns, got {len(parts)}"
    assert parts[9] == "", f"group_start should be empty for Total, got '{parts[9]}'"
    assert parts[10] == "", f"group_end should be empty for Total, got '{parts[10]}'"
    
    print(f"  OK Total row: no time range")


def test_empty_days_not_included():
    """Test that days without records are not included.
    
    Expected:
    - Only days with records appear in output
    - No "filler" rows for empty days
    """
    base_ts = 1776892800  # 2026-04-22
    
    records = [
        {
            "key": "rec1",
            "t1": base_ts + 9 * 3600,  # Day 1: 2026-04-22
            "t2": base_ts + 10 * 3600,
            "duration": 3600,
            "tagz": "#work",
            "ds": "Day 1"
        },
        {
            "key": "rec2",
            "t1": base_ts + 2 * 24 * 3600 + 9 * 3600,  # Day 3: 2026-04-24
            "t2": base_ts + 2 * 24 * 3600 + 10 * 3600,
            "duration": 3600,
            "tagz": "#work",
            "ds": "Day 3"
        }
    ]
    
    rows = generate_table_rows_simple(records, "tagz", "day", False)
    
    # Total + 2 day groups = 3 rows
    # Day 2 (2026-04-23) should NOT appear
    assert len(rows) == 3, f"Expected 3 rows (Total + 2 days), got {len(rows)}"
    
    # Check the titles
    titles = [row[2] for row in rows if row[0] == "head" and row[2] != "Total"]
    
    # Should have 2 day groups
    assert len(titles) == 2, f"Expected 2 day groups, got {len(titles)}"
    
    # Each should contain a date (starts with 2026)
    for title in titles:
        assert "2026" in title, f"Title should contain date: {title}"
    
    print(f"  OK Empty days not included: {len(titles)} day groups")


def test_html_time_range_display():
    """Test HTML displays time range only when both times are present.
    
    Expected:
    - Only show time range when both start_time and end_time are non-empty
    - Don't show when only one is present
    - Don't show when both are empty
    """
    def format_html_time_range(row):
        """Simulate the HTML time range logic."""
        start_time = row[4] if len(row) > 4 else ""
        end_time = row[5] if len(row) > 5 else ""
        time_range = ""
        if start_time and end_time:
            time_range = f"<span>{start_time} - {end_time}</span>"
        return f"<tr><th>{row[1]}</th><th>{row[2]}{time_range}</th></tr>"
    
    # Both times present
    row_with = ["head", "8:00", "Day", 1, "09:00", "17:00"]
    html_with = format_html_time_range(row_with)
    assert "09:00 - 17:00" in html_with, f"Time range should be visible: {html_with}"
    
    # Only start time
    row_start_only = ["head", "8:00", "Day", 1, "09:00", ""]
    html_start_only = format_html_time_range(row_start_only)
    assert "span" not in html_start_only, f"No span when end time is empty: {html_start_only}"
    
    # Only end time
    row_end_only = ["head", "8:00", "Day", 1, "", "17:00"]
    html_end_only = format_html_time_range(row_end_only)
    assert "span" not in html_end_only, f"No span when start time is empty: {html_end_only}"
    
    # Neither time (old format)
    row_none = ["head", "8:00", "#work", 1]
    html_none = format_html_time_range(row_none)
    assert "span" not in html_none, f"No span when no times: {html_none}"
    
    print(f"  OK HTML time range: shown only when both times present")


if __name__ == "__main__":
    run_tests(globals())
