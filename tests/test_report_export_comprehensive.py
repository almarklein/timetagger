"""Comprehensive test for report dialog export functionality.

This test verifies:
1. PDF export logic (condition-based display)
2. CSV export column order and backward compatibility
3. Different grouping methods (tagz, ds, none)
4. Different period groupings (day, week, month)
5. Edge cases and boundary conditions
"""

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
    dt_obj = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt_obj.strftime("%Y-%m-%d %H:%M:%S")


def format_isodate(date_str):
    """Format ISO date (simplified)."""
    return date_str


def generate_table_rows(records, group_method, group_period, showrecords=False):
    """Simulate the _generate_table_rows logic (full version)."""
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


# ============================================================================
# CSV Export Tests
# ============================================================================

CSV_HEADER = "subtotals,tag_groups,duration,date,start,stop,description,user,tags,group_start,group_end"

def format_csv_row(row):
    """Simulate CSV row formatting from _save_as_csv."""
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


def test_csv_header_columns():
    """Test CSV header has correct column order.
    
    Expected columns (11 total):
    0: subtotals
    1: tag_groups
    2: duration
    3: date
    4: start
    5: stop
    6: description
    7: user
    8: tags
    9: group_start (NEW)
    10: group_end (NEW)
    """
    columns = CSV_HEADER.split(",")
    
    assert len(columns) == 11, f"Expected 11 columns, got {len(columns)}"
    assert columns[0] == "subtotals", f"Column 0 should be 'subtotals', got {columns[0]}"
    assert columns[1] == "tag_groups", f"Column 1 should be 'tag_groups', got {columns[1]}"
    assert columns[2] == "duration", f"Column 2 should be 'duration', got {columns[2]}"
    assert columns[3] == "date", f"Column 3 should be 'date', got {columns[3]}"
    assert columns[4] == "start", f"Column 4 should be 'start', got {columns[4]}"
    assert columns[5] == "stop", f"Column 5 should be 'stop', got {columns[5]}"
    assert columns[6] == "description", f"Column 6 should be 'description', got {columns[6]}"
    assert columns[7] == "user", f"Column 7 should be 'user', got {columns[7]}"
    assert columns[8] == "tags", f"Column 8 should be 'tags', got {columns[8]}"
    assert columns[9] == "group_start", f"Column 9 should be 'group_start', got {columns[9]}"
    assert columns[10] == "group_end", f"Column 10 should be 'group_end', got {columns[10]}"
    
    print(f"  OK CSV header: 11 columns, new columns at positions 9 and 10")


def test_csv_head_row_format():
    """Test CSV head row formatting for both old and new formats.
    
    Head row format:
    - Column 0: subtotals (duration)
    - Column 1: tag_groups (title)
    - Columns 2-8: empty
    - Column 9: group_start (if available)
    - Column 10: group_end (if available)
    """
    # New format with time range (6 elements)
    new_row = ["head", "5:30", "2026-04-22 / #work", 1, "09:00", "17:30"]
    csv = format_csv_row(new_row)
    parts = csv.split(",")
    
    assert len(parts) == 11, f"Expected 11 columns, got {len(parts)}"
    assert parts[0] == "5:30", f"Column 0 (subtotals) should be '5:30', got {parts[0]}"
    assert parts[1] == "2026-04-22 / #work", f"Column 1 (tag_groups) wrong: {parts[1]}"
    assert parts[2] == "", f"Column 2 (duration) should be empty for head row, got '{parts[2]}'"
    assert parts[3] == "", f"Column 3 (date) should be empty for head row, got '{parts[3]}'"
    assert parts[4] == "", f"Column 4 (start) should be empty for head row, got '{parts[4]}'"
    assert parts[5] == "", f"Column 5 (stop) should be empty for head row, got '{parts[5]}'"
    assert parts[6] == "", f"Column 6 (description) should be empty for head row, got '{parts[6]}'"
    assert parts[7] == "", f"Column 7 (user) should be empty for head row, got '{parts[7]}'"
    assert parts[8] == "", f"Column 8 (tags) should be empty for head row, got '{parts[8]}'"
    assert parts[9] == "09:00", f"Column 9 (group_start) should be '09:00', got '{parts[9]}'"
    assert parts[10] == "17:30", f"Column 10 (group_end) should be '17:30', got '{parts[10]}'"
    
    # Old format without time range (4 elements) - backward compatibility
    old_row = ["head", "3:00", "#meeting", 1]
    csv_old = format_csv_row(old_row)
    parts_old = csv_old.split(",")
    
    assert len(parts_old) == 11, f"Expected 11 columns for old format, got {len(parts_old)}"
    assert parts_old[0] == "3:00", f"Old format: Column 0 should be '3:00', got {parts_old[0]}"
    assert parts_old[1] == "#meeting", f"Old format: Column 1 should be '#meeting', got {parts_old[1]}"
    assert parts_old[9] == "", f"Old format: Column 9 should be empty, got '{parts_old[9]}'"
    assert parts_old[10] == "", f"Old format: Column 10 should be empty, got '{parts_old[10]}'"
    
    print(f"  OK CSV head row: new and old formats work correctly")


def test_csv_record_row_format():
    """Test CSV record row formatting.
    
    Record row format:
    - Column 0-1: empty
    - Column 2: duration
    - Column 3: date
    - Column 4: start
    - Column 5: stop
    - Column 6: description (quoted)
    - Column 7: user
    - Column 8: tags
    - Column 9-10: empty (no group_start/group_end for individual records)
    """
    record_row = [
        "record",
        "key1",
        "1:00",
        "2026-04-22",
        "09:00",
        "10:00",
        "Work description",
        "#work #meeting"
    ]
    
    csv = format_csv_row(record_row)
    parts = csv.split(",")
    
    # Quoted description may have commas, let's verify structure
    assert parts[0] == "", f"Record row: Column 0 should be empty, got '{parts[0]}'"
    assert parts[1] == "", f"Record row: Column 1 should be empty, got '{parts[1]}'"
    assert parts[2] == "1:00", f"Record row: Column 2 (duration) should be '1:00', got {parts[2]}"
    assert parts[3] == "2026-04-22", f"Record row: Column 3 (date) should be '2026-04-22', got {parts[3]}"
    assert parts[4] == "09:00", f"Record row: Column 4 (start) should be '09:00', got {parts[4]}"
    assert parts[5] == "10:00", f"Record row: Column 5 (stop) should be '10:00', got {parts[5]}"
    
    # Verify the quoted description
    assert '"Work description"' in csv, f"Description should be quoted: {csv}"
    
    # Verify the last two columns are empty for record rows
    # (the last two commas represent empty group_start and group_end)
    assert csv.endswith(",,"), f"Record row should end with two empty columns: {csv}"
    
    print(f"  OK CSV record row: format is correct")


def test_csv_blank_row_format():
    """Test CSV blank row formatting."""
    blank_row = ["blank"]
    csv = format_csv_row(blank_row)
    parts = csv.split(",")
    
    assert len(parts) == 11, f"Blank row should have 11 columns, got {len(parts)}"
    for i, part in enumerate(parts):
        assert part == "", f"Blank row: Column {i} should be empty, got '{part}'"
    
    print(f"  OK CSV blank row: all columns empty")


def test_csv_total_row_format():
    """Test CSV Total row formatting.
    
    Total row is a head row with only 4 elements (no time range).
    """
    total_row = ["head", "8:00", "Total", 0]
    csv = format_csv_row(total_row)
    parts = csv.split(",")
    
    assert len(parts) == 11, f"Total row should have 11 columns, got {len(parts)}"
    assert parts[0] == "8:00", f"Total row: Column 0 (subtotals) should be '8:00', got {parts[0]}"
    assert parts[1] == "Total", f"Total row: Column 1 (tag_groups) should be 'Total', got {parts[1]}"
    assert parts[9] == "", f"Total row: Column 9 (group_start) should be empty, got '{parts[9]}'"
    assert parts[10] == "", f"Total row: Column 10 (group_end) should be empty, got '{parts[10]}'"
    
    print(f"  OK CSV Total row: no time range")


# ============================================================================
# PDF Export Tests (Logic Only)
# ============================================================================

def format_pdf_time_range(row):
    """Simulate PDF time range logic from _save_as_pdf.
    
    The actual PDF rendering uses jsPDF, but we can verify:
    1. When start_time and end_time are present, show them
    2. When either is missing, don't show
    3. Non-period grouping should not have time range
    """
    start_time = row[4] if len(row) > 4 else ""
    end_time = row[5] if len(row) > 5 else ""
    
    should_show = bool(start_time and end_time)
    time_range_text = f"  {start_time} - {end_time}" if should_show else ""
    
    return {
        "should_show": should_show,
        "start_time": start_time,
        "end_time": end_time,
        "time_range_text": time_range_text
    }


def test_pdf_time_range_display_logic():
    """Test PDF time range display logic.
    
    In _save_as_pdf, the logic is:
    - start_time = row[4] if len(row) > 4 else ""
    - end_time = row[5] if len(row) > 5 else ""
    - Only show if start_time and end_time are both truthy
    """
    # Case 1: Both times present (day grouping)
    row_with_time = ["head", "5:30", "2026-04-22", 1, "09:00", "17:30"]
    result = format_pdf_time_range(row_with_time)
    
    assert result["should_show"] == True, "Should show time range when both times present"
    assert result["start_time"] == "09:00", f"start_time should be '09:00', got {result['start_time']}"
    assert result["end_time"] == "17:30", f"end_time should be '17:30', got {result['end_time']}"
    assert "09:00 - 17:30" in result["time_range_text"], "Time range text should contain both times"
    
    # Case 2: Old format (4 elements, no time range)
    row_old_format = ["head", "3:00", "#work", 1]
    result_old = format_pdf_time_range(row_old_format)
    
    assert result_old["should_show"] == False, "Old format should not show time range"
    assert result_old["start_time"] == "", f"Old format start_time should be empty, got '{result_old['start_time']}'"
    assert result_old["end_time"] == "", f"Old format end_time should be empty, got '{result_old['end_time']}'"
    assert result_old["time_range_text"] == "", "Old format should have empty time range text"
    
    # Case 3: Only start_time present (edge case)
    row_start_only = ["head", "2:00", "Day", 1, "09:00", ""]
    result_start = format_pdf_time_range(row_start_only)
    
    assert result_start["should_show"] == False, "Should not show when only start_time present"
    
    # Case 4: Only end_time present (edge case)
    row_end_only = ["head", "2:00", "Day", 1, "", "17:00"]
    result_end = format_pdf_time_range(row_end_only)
    
    assert result_end["should_show"] == False, "Should not show when only end_time present"
    
    # Case 5: Total row (no time range)
    row_total = ["head", "10:30", "Total", 0]
    result_total = format_pdf_time_range(row_total)
    
    assert result_total["should_show"] == False, "Total row should not show time range"
    
    print(f"  OK PDF time range logic: correct conditional display")


# ============================================================================
# Grouping Method Tests
# ============================================================================

def test_group_method_tagz_with_day_period():
    """Test grouping by tagz with day period.
    
    Expected:
    - Each tag group is further grouped by day
    - Each day/tag combination has its own min_t1/max_t2
    """
    base_ts = 1776936000  # 2026-04-22 12:00:00 UTC
    
    records = [
        {
            "key": "rec1",
            "t1": base_ts,  # 12:00
            "t2": base_ts + 3600,  # 13:00
            "duration": 3600,
            "tagz": "#work",
            "ds": "Work 1"
        },
        {
            "key": "rec2",
            "t1": base_ts + 5400,  # 13:30
            "t2": base_ts + 9000,  # 14:30
            "duration": 3600,
            "tagz": "#meeting",
            "ds": "Meeting 1"
        },
        {
            "key": "rec3",
            "t1": base_ts + 10800,  # 15:00
            "t2": base_ts + 14400,  # 16:00
            "duration": 3600,
            "tagz": "#work",
            "ds": "Work 2"
        }
    ]
    
    rows = generate_table_rows(records, "tagz", "day", False)
    
    # Get non-Total head rows
    head_rows = [r for r in rows if r[0] == "head" and r[2] != "Total"]
    
    # Should have 2 groups: "#work" and "#meeting", each grouped by day
    assert len(head_rows) == 2, f"Expected 2 day groups, got {len(head_rows)}"
    
    # Each should have time range (6 elements)
    for row in head_rows:
        assert len(row) == 6, f"Day group row should have 6 elements, got {len(row)}"
        assert row[4], f"start_time should not be empty for day group"
        assert row[5], f"end_time should not be empty for day group"
        assert row[4] < row[5], f"start_time ({row[4]}) should be earlier than end_time ({row[5]})"
    
    print(f"  OK Group method 'tagz' with 'day' period: {len(head_rows)} groups, all have time ranges")


def test_group_method_none_with_day_period():
    """Test grouping method 'none' with day period.
    
    Expected:
    - No primary grouping, all records in one "hidden" group
    - Secondary grouping by day
    - Each day has time range
    """
    base_ts = 1776936000  # 2026-04-22 12:00:00 UTC
    
    records = [
        {
            "key": "rec1",
            "t1": base_ts,  # 12:00
            "t2": base_ts + 3600,  # 13:00
            "duration": 3600,
            "tagz": "#work",
            "ds": "Work"
        },
        {
            "key": "rec2",
            "t1": base_ts + 7200,  # 14:00
            "t2": base_ts + 10800,  # 15:00
            "duration": 3600,
            "tagz": "#meeting",
            "ds": "Meeting"
        }
    ]
    
    rows = generate_table_rows(records, "none", "day", False)
    
    head_rows = [r for r in rows if r[0] == "head" and r[2] != "Total"]
    
    # With "none" grouping, all records are in "hidden" group
    # So we should have 1 day group
    assert len(head_rows) == 1, f"Expected 1 day group with 'none' grouping, got {len(head_rows)}"
    
    row = head_rows[0]
    assert len(row) == 6, f"Day group should have 6 elements, got {len(row)}"
    assert row[4], f"start_time should not be empty"
    assert row[5], f"end_time should not be empty"
    
    # The time range should cover all records in the day
    # Expected start: earliest t1 (12:00)
    # Expected end: latest t2 (15:00)
    expected_start = time2localstr(base_ts).split(" ")[1][:5]
    expected_end = time2localstr(base_ts + 10800).split(" ")[1][:5]
    
    assert row[4] == expected_start, f"start_time should be '{expected_start}', got '{row[4]}'"
    assert row[5] == expected_end, f"end_time should be '{expected_end}', got '{row[5]}'"
    
    print(f"  OK Group method 'none' with 'day' period: time range covers all records")


def test_group_method_tagz_with_no_period():
    """Test grouping by tagz with no time period.
    
    Expected:
    - No min_t1/max_t2 calculation
    - Rows have 6 elements (consistent format), but time fields are empty
    - CSV/PDF/HTML should not show time range when fields are empty
    """
    base_ts = 1776936000
    
    records = [
        {
            "key": "rec1",
            "t1": base_ts,
            "t2": base_ts + 3600,
            "duration": 3600,
            "tagz": "#work",
            "ds": "Work"
        }
    ]
    
    rows = generate_table_rows(records, "tagz", "none", False)
    
    head_rows = [r for r in rows if r[0] == "head" and r[2] != "Total"]
    
    assert len(head_rows) == 1, f"Expected 1 tag group, got {len(head_rows)}"
    
    row = head_rows[0]
    # With no period grouping, the row has 6 elements (consistent format)
    # but min_t1/max_t2 are None, so time fields are empty strings
    assert len(row) == 6, f"Non-period group row should have 6 elements (consistent format), got {len(row)}"
    
    # The important part: time fields should be empty
    assert row[4] == "", f"start_time should be empty for non-period grouping, got '{row[4]}'"
    assert row[5] == "", f"end_time should be empty for non-period grouping, got '{row[5]}'"
    
    # Verify CSV formatting handles empty time fields
    csv = format_csv_row(row)
    parts = csv.split(",")
    assert parts[9] == "", f"CSV group_start should be empty, got '{parts[9]}'"
    assert parts[10] == "", f"CSV group_end should be empty, got '{parts[10]}'"
    
    # Verify PDF logic doesn't show time range
    pdf_result = format_pdf_time_range(row)
    assert pdf_result["should_show"] == False, "PDF should not show time range for non-period grouping"
    
    print(f"  OK Group method 'tagz' with no period: time fields are empty, no display")


# ============================================================================
# Edge Case Tests
# ============================================================================

def test_single_record_day():
    """Test a single record in a day.
    
    Expected:
    - start_time = record.t1
    - end_time = record.t2
    """
    base_ts = 1776936000
    
    records = [
        {
            "key": "rec1",
            "t1": base_ts + 3600,  # 13:00
            "t2": base_ts + 7200,  # 14:00
            "duration": 3600,
            "tagz": "#work",
            "ds": "Single record"
        }
    ]
    
    rows = generate_table_rows(records, "tagz", "day", False)
    
    head_rows = [r for r in rows if r[0] == "head" and r[2] != "Total"]
    
    assert len(head_rows) == 1, f"Expected 1 day group, got {len(head_rows)}"
    
    row = head_rows[0]
    assert len(row) == 6, f"Day group should have 6 elements, got {len(row)}"
    
    expected_start = time2localstr(base_ts + 3600).split(" ")[1][:5]
    expected_end = time2localstr(base_ts + 7200).split(" ")[1][:5]
    
    assert row[4] == expected_start, f"start_time should be '{expected_start}', got '{row[4]}'"
    assert row[5] == expected_end, f"end_time should be '{expected_end}', got '{row[5]}'"
    
    print(f"  OK Single record day: start={row[4]}, end={row[5]}")


def test_multiple_records_out_of_order():
    """Test records added out of chronological order.
    
    Expected:
    - min_t1 = earliest t1 regardless of addition order
    - max_t2 = latest t2 regardless of addition order
    """
    base_ts = 1776936000
    
    # Records in reverse chronological order
    records = [
        {
            "key": "rec3",
            "t1": base_ts + 7200,  # 14:00 (middle)
            "t2": base_ts + 10800,  # 15:00
            "duration": 3600,
            "tagz": "#work",
            "ds": "Middle"
        },
        {
            "key": "rec1",
            "t1": base_ts,  # 12:00 (earliest)
            "t2": base_ts + 3600,  # 13:00
            "duration": 3600,
            "tagz": "#work",
            "ds": "Earliest"
        },
        {
            "key": "rec4",
            "t1": base_ts + 5400,  # 13:30
            "t2": base_ts + 14400,  # 16:00 (latest)
            "duration": 9000,
            "tagz": "#work",
            "ds": "Latest end"
        },
        {
            "key": "rec2",
            "t1": base_ts + 1800,  # 12:30
            "t2": base_ts + 5400,  # 13:30
            "duration": 3600,
            "tagz": "#work",
            "ds": "Early middle"
        }
    ]
    
    rows = generate_table_rows(records, "tagz", "day", False)
    
    head_rows = [r for r in rows if r[0] == "head" and r[2] != "Total"]
    
    assert len(head_rows) == 1, f"Expected 1 day group, got {len(head_rows)}"
    
    row = head_rows[0]
    
    # Expected: earliest t1 is base_ts (12:00), latest t2 is base_ts + 14400 (16:00)
    expected_start = time2localstr(base_ts).split(" ")[1][:5]
    expected_end = time2localstr(base_ts + 14400).split(" ")[1][:5]
    
    assert row[4] == expected_start, f"start_time should be '{expected_start}', got '{row[4]}'"
    assert row[5] == expected_end, f"end_time should be '{expected_end}', got '{row[5]}'"
    
    print(f"  OK Out-of-order records: start={row[4]}, end={row[5]} (correct min/max)")


def test_different_days_separate():
    """Test records on different days are separate.
    
    Expected:
    - Each day has its own group
    - Each day has its own min_t1/max_t2
    - Days without records don't appear
    """
    base_ts = 1776892800  # 2026-04-22 00:00:00 UTC
    
    records = [
        # Day 1: 2026-04-22
        {
            "key": "rec1",
            "t1": base_ts + 12 * 3600,  # 12:00
            "t2": base_ts + 13 * 3600,  # 13:00
            "duration": 3600,
            "tagz": "#work",
            "ds": "Day 1"
        },
        # Day 3: 2026-04-24 (skip day 2)
        {
            "key": "rec2",
            "t1": base_ts + 2 * 24 * 3600 + 14 * 3600,  # 14:00 on day 3
            "t2": base_ts + 2 * 24 * 3600 + 16 * 3600,  # 16:00 on day 3
            "duration": 7200,
            "tagz": "#work",
            "ds": "Day 3"
        }
    ]
    
    rows = generate_table_rows(records, "tagz", "day", False)
    
    head_rows = [r for r in rows if r[0] == "head" and r[2] != "Total"]
    
    # Should have 2 day groups (Day 1 and Day 3)
    # Day 2 should NOT appear
    assert len(head_rows) == 2, f"Expected 2 day groups, got {len(head_rows)}"
    
    # Each day should have its own time range
    day1_row = head_rows[0]
    day3_row = head_rows[1]
    
    assert len(day1_row) == 6, f"Day 1 row should have 6 elements"
    assert len(day3_row) == 6, f"Day 3 row should have 6 elements"
    
    # Day 1: 12:00 - 13:00
    expected_day1_start = time2localstr(base_ts + 12 * 3600).split(" ")[1][:5]
    expected_day1_end = time2localstr(base_ts + 13 * 3600).split(" ")[1][:5]
    
    # Day 3: 14:00 - 16:00
    expected_day3_start = time2localstr(base_ts + 2 * 24 * 3600 + 14 * 3600).split(" ")[1][:5]
    expected_day3_end = time2localstr(base_ts + 2 * 24 * 3600 + 16 * 3600).split(" ")[1][:5]
    
    assert day1_row[4] == expected_day1_start, f"Day 1 start_time wrong"
    assert day1_row[5] == expected_day1_end, f"Day 1 end_time wrong"
    
    assert day3_row[4] == expected_day3_start, f"Day 3 start_time wrong"
    assert day3_row[5] == expected_day3_end, f"Day 3 end_time wrong"
    
    print(f"  OK Different days: 2 day groups (Day 2 skipped), each with own time range")


# ============================================================================
# Backward Compatibility Tests
# ============================================================================

def test_backward_compatible_old_format_rows():
    """Test that old format rows (4 elements) work correctly.
    
    This simulates the scenario where:
    - Non-period grouping (no time range)
    - Total row (no time range)
    
    Both HTML and CSV should handle these correctly.
    """
    # Old format head row (4 elements)
    old_row = ["head", "2:30", "#work", 1]
    
    # CSV formatting
    csv = format_csv_row(old_row)
    parts = csv.split(",")
    
    assert len(parts) == 11, f"Old format should produce 11 columns, got {len(parts)}"
    assert parts[0] == "2:30", f"Column 0 should be '2:30', got {parts[0]}"
    assert parts[1] == "#work", f"Column 1 should be '#work', got {parts[1]}"
    assert parts[9] == "", f"Column 9 (group_start) should be empty for old format"
    assert parts[10] == "", f"Column 10 (group_end) should be empty for old format"
    
    # PDF logic
    pdf_result = format_pdf_time_range(old_row)
    assert pdf_result["should_show"] == False, "Old format should not show time range in PDF"
    
    # HTML logic (simulated)
    def format_html(row):
        start_time = row[4] if len(row) > 4 else ""
        end_time = row[5] if len(row) > 5 else ""
        time_range = ""
        if start_time and end_time:
            time_range = f"<span>{start_time} - {end_time}</span>"
        return time_range
    
    html_time_range = format_html(old_row)
    assert html_time_range == "", "Old format should not show time range in HTML"
    
    print(f"  OK Backward compatibility: old format (4 elements) works correctly")


def test_backward_compatible_column_order():
    """Test that original columns are in the same order.
    
    The original CSV columns (before adding group_start/group_end) were:
    subtotals,tag_groups,duration,date,start,stop,description,user,tags
    
    These should remain in the same order, with new columns added at the end.
    """
    # Create a new format row with time range
    new_row = ["head", "4:00", "2026-04-22 / #work", 1, "09:00", "17:00"]
    
    csv = format_csv_row(new_row)
    parts = csv.split(",")
    
    # Verify original columns are in correct positions
    # Column 0: subtotals (was duration in head rows)
    # Column 1: tag_groups (was title)
    # Column 2-8: empty for head rows (duration, date, start, stop, description, user, tags)
    # Column 9-10: NEW (group_start, group_end)
    
    assert parts[0] == "4:00", f"Original column 0 (subtotals) should be '4:00'"
    assert parts[1] == "2026-04-22 / #work", f"Original column 1 (tag_groups) should contain title"
    
    # Original columns 2-8 should be empty for head rows
    for i in range(2, 9):
        assert parts[i] == "", f"Original column {i} should be empty for head row, got '{parts[i]}'"
    
    # New columns 9-10 should have time values
    assert parts[9] == "09:00", f"New column 9 (group_start) should be '09:00'"
    assert parts[10] == "17:00", f"New column 10 (group_end) should be '17:00'"
    
    print(f"  OK Column order preserved: original columns unchanged, new columns at end")


if __name__ == "__main__":
    run_tests(globals())
