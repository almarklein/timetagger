"""Direct tests for report_utils.py - the shared report utility module.

These tests directly call the functions in report_utils.py,
not a simulated copy. This verifies the real implementation.

Test coverage:
1. Day grouping with multiple records: earliest start, latest end
2. Non-period grouping: no time range
3. Empty days: not included
4. CSV export: column order, backward compatibility
5. HTML/PDF display logic: conditional time range
"""

from _common import run_tests

from timetagger.app import dt
from timetagger.app import report_utils


def test_day_grouping_multiple_records():
    """Test day grouping with multiple records on the same day.
    
    Expected:
    - start_time = earliest record's t1
    - end_time = latest record's t2
    """
    base_ts = 1776936000  # 2026-04-22 12:00:00 UTC
    
    records = [
        {
            "key": "rec1",
            "t1": base_ts,  # 12:00 (earliest start)
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
            "t1": base_ts + 5400,  # 13:30
            "t2": base_ts + 14400,  # 16:00 (latest end)
            "duration": 9000,
            "tagz": "#work",
            "ds": "Last (latest end)"
        }
    ]
    
    rows = report_utils.generate_report_rows(
        records,
        group_method="tagz",
        group_period="day",
        showrecords=False,
        dt=dt,
    )
    
    head_rows = [r for r in rows if r[0] == "head" and r[2] != "Total"]
    
    assert len(head_rows) == 1, f"Expected 1 day group, got {len(head_rows)}"
    
    day_row = head_rows[0]
    
    assert len(day_row) == 6, f"Day group should have 6 elements, got {len(day_row)}"
    
    start_time = day_row[4]
    end_time = day_row[5]
    
    assert start_time, f"start_time should not be empty"
    assert end_time, f"end_time should not be empty"
    
    expected_start = dt.time2localstr(base_ts).split(" ")[1][:5]
    expected_end = dt.time2localstr(base_ts + 14400).split(" ")[1][:5]
    
    assert start_time == expected_start, f"Expected start_time '{expected_start}', got '{start_time}'"
    assert end_time == expected_end, f"Expected end_time '{expected_end}', got '{end_time}'"
    
    print(f"  OK Day grouping multiple records: start={start_time}, end={end_time}")


def test_non_period_grouping_no_time_range():
    """Test that non-period grouping does not show time ranges.
    
    Expected:
    - Time fields are empty strings
    - CSV/PDF/HTML should not show time range
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
    
    rows = report_utils.generate_report_rows(
        records,
        group_method="tagz",
        group_period="none",
        showrecords=False,
        dt=dt,
    )
    
    head_rows = [r for r in rows if r[0] == "head" and r[2] != "Total"]
    
    assert len(head_rows) == 1, f"Expected 1 tag group, got {len(head_rows)}"
    
    tag_row = head_rows[0]
    
    assert len(tag_row) == 6, f"Tag group should have 6 elements (consistent format), got {len(tag_row)}"
    
    assert tag_row[4] == "", f"start_time should be empty for non-period grouping, got '{tag_row[4]}'"
    assert tag_row[5] == "", f"end_time should be empty for non-period grouping, got '{tag_row[5]}'"
    
    should_show, _, _ = report_utils.should_show_time_range(tag_row)
    assert should_show == False, "should_show_time_range should be False for non-period grouping"
    
    csv = report_utils.format_csv_row(tag_row)
    parts = csv.split(",")
    assert parts[9] == "", f"CSV group_start should be empty, got '{parts[9]}'"
    assert parts[10] == "", f"CSV group_end should be empty, got '{parts[10]}'"
    
    html = report_utils.format_html_time_range(tag_row)
    assert html == "", f"HTML time range should be empty, got '{html}'"
    
    pdf_show, _ = report_utils.format_pdf_time_range(tag_row)
    assert pdf_show == False, "PDF should not show time range for non-period grouping"
    
    print(f"  OK Non-period grouping: time fields empty, no display")


def test_empty_days_not_included():
    """Test that days without records are not included.
    
    Expected:
    - Only days with records appear
    - No filler rows for empty days
    """
    base_ts = 1776892800  # 2026-04-22 00:00:00 UTC
    
    records = [
        {
            "key": "rec1",
            "t1": base_ts + 12 * 3600,  # Day 1: 2026-04-22
            "t2": base_ts + 13 * 3600,
            "duration": 3600,
            "tagz": "#work",
            "ds": "Day 1"
        },
        {
            "key": "rec2",
            "t1": base_ts + 2 * 24 * 3600 + 12 * 3600,  # Day 3: 2026-04-24
            "t2": base_ts + 2 * 24 * 3600 + 13 * 3600,
            "duration": 3600,
            "tagz": "#work",
            "ds": "Day 3"
        }
    ]
    
    rows = report_utils.generate_report_rows(
        records,
        group_method="tagz",
        group_period="day",
        showrecords=False,
        dt=dt,
    )
    
    head_rows = [r for r in rows if r[0] == "head" and r[2] != "Total"]
    
    assert len(head_rows) == 2, f"Expected 2 day groups (Total + 2 days), got {len(head_rows)}"
    
    for row in head_rows:
        assert row[4], f"Day group should have start_time: {row}"
        assert row[5], f"Day group should have end_time: {row}"
    
    print(f"  OK Empty days not included: {len(head_rows)} day groups")


def test_total_row_no_time_range():
    """Test that Total row does not have time range.
    
    Expected:
    - Total row has only 4 elements
    - No time range in any export format
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
    
    rows = report_utils.generate_report_rows(
        records,
        group_method="tagz",
        group_period="day",
        showrecords=False,
        dt=dt,
    )
    
    total_row = rows[0]
    
    assert total_row[2] == "Total", f"First row should be Total, got {total_row[2]}"
    assert len(total_row) == 4, f"Total row should have 4 elements, got {len(total_row)}"
    
    should_show, _, _ = report_utils.should_show_time_range(total_row)
    assert should_show == False, "should_show_time_range should be False for Total row"
    
    csv = report_utils.format_csv_row(total_row)
    parts = csv.split(",")
    assert parts[9] == "", f"CSV group_start should be empty for Total, got '{parts[9]}'"
    assert parts[10] == "", f"CSV group_end should be empty for Total, got '{parts[10]}'"
    
    html = report_utils.format_html_time_range(total_row)
    assert html == "", f"HTML time range should be empty for Total"
    
    print(f"  OK Total row: no time range")


def test_csv_column_order():
    """Test CSV column order is preserved.
    
    Columns (11 total):
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
    assert report_utils.CSV_HEADER == "subtotals,tag_groups,duration,date,start,stop,description,user,tags,group_start,group_end"
    
    parts = report_utils.CSV_HEADER.split(",")
    assert len(parts) == 11, f"Expected 11 columns, got {len(parts)}"
    
    assert parts[0] == "subtotals"
    assert parts[1] == "tag_groups"
    assert parts[2] == "duration"
    assert parts[3] == "date"
    assert parts[4] == "start"
    assert parts[5] == "stop"
    assert parts[6] == "description"
    assert parts[7] == "user"
    assert parts[8] == "tags"
    assert parts[9] == "group_start"
    assert parts[10] == "group_end"
    
    print(f"  OK CSV header: 11 columns, new columns at positions 9 and 10")


def test_csv_head_row_with_time():
    """Test CSV head row with time range.
    
    Expected:
    - Column 0: duration (subtotals)
    - Column 1: title (tag_groups)
    - Columns 2-8: empty
    - Column 9: group_start
    - Column 10: group_end
    """
    row_with_time = ["head", "8:00", "2026-04-22 / #work", 1, "09:00", "17:00"]
    
    csv = report_utils.format_csv_row(row_with_time)
    parts = csv.split(",")
    
    assert len(parts) == 11, f"Expected 11 columns, got {len(parts)}"
    assert parts[0] == "8:00", f"Column 0 (subtotals) should be '8:00', got '{parts[0]}'"
    assert parts[1] == "2026-04-22 / #work", f"Column 1 (tag_groups) wrong: {parts[1]}"
    assert parts[2] == "", f"Column 2 (duration) should be empty for head row"
    assert parts[3] == "", f"Column 3 (date) should be empty for head row"
    assert parts[4] == "", f"Column 4 (start) should be empty for head row"
    assert parts[5] == "", f"Column 5 (stop) should be empty for head row"
    assert parts[6] == "", f"Column 6 (description) should be empty for head row"
    assert parts[7] == "", f"Column 7 (user) should be empty for head row"
    assert parts[8] == "", f"Column 8 (tags) should be empty for head row"
    assert parts[9] == "09:00", f"Column 9 (group_start) should be '09:00', got '{parts[9]}'"
    assert parts[10] == "17:00", f"Column 10 (group_end) should be '17:00', got '{parts[10]}'"
    
    print(f"  OK CSV head row with time: correct column order")


def test_csv_head_row_without_time():
    """Test CSV head row without time range (backward compatibility).
    
    Expected:
    - Column 9 and 10 are empty
    """
    row_no_time = ["head", "3:00", "#meeting", 1]
    
    csv = report_utils.format_csv_row(row_no_time)
    parts = csv.split(",")
    
    assert len(parts) == 11, f"Expected 11 columns, got {len(parts)}"
    assert parts[0] == "3:00", f"Column 0 should be '3:00', got '{parts[0]}'"
    assert parts[1] == "#meeting", f"Column 1 should be '#meeting', got '{parts[1]}'"
    assert parts[9] == "", f"Column 9 (group_start) should be empty, got '{parts[9]}'"
    assert parts[10] == "", f"Column 10 (group_end) should be empty, got '{parts[10]}'"
    
    print(f"  OK CSV head row without time: backward compatible")


def test_csv_record_row():
    """Test CSV record row.
    
    Expected:
    - Columns 0-1: empty
    - Column 2: duration
    - Column 3: date
    - Column 4: start
    - Column 5: stop
    - Column 6: description (quoted)
    - Column 7: user
    - Column 8: tags
    - Columns 9-10: empty (no group_start/group_end for individual records)
    """
    record_row = [
        "record",
        "key1",
        "1:00",
        "2026-04-22",
        "09:00",
        "10:00",
        "Work description",
        "#work"
    ]
    
    csv = report_utils.format_csv_row(record_row, user="testuser")
    parts = csv.split(",")
    
    assert len(parts) >= 11, f"Expected at least 11 columns, got {len(parts)}"
    assert parts[0] == "", f"Column 0 should be empty for record row, got '{parts[0]}'"
    assert parts[1] == "", f"Column 1 should be empty for record row, got '{parts[1]}'"
    assert parts[2] == "1:00", f"Column 2 (duration) should be '1:00', got '{parts[2]}'"
    assert parts[3] == "2026-04-22", f"Column 3 (date) should be '2026-04-22', got '{parts[3]}'"
    assert parts[4] == "09:00", f"Column 4 (start) should be '09:00', got '{parts[4]}'"
    assert parts[5] == "10:00", f"Column 5 (stop) should be '10:00', got '{parts[5]}'"
    
    assert '"Work description"' in csv, f"Description should be quoted: {csv}"
    
    assert csv.endswith(",,"), f"Record row should end with two empty columns: {csv}"
    
    print(f"  OK CSV record row: correct format")


def test_csv_blank_row():
    """Test CSV blank row."""
    blank_row = ["blank"]
    
    csv = report_utils.format_csv_row(blank_row)
    parts = csv.split(",")
    
    assert len(parts) == 11, f"Expected 11 columns, got {len(parts)}"
    for i, p in enumerate(parts):
        assert p == "", f"Column {i} should be empty for blank row, got '{p}'"
    
    print(f"  OK CSV blank row: all columns empty")


def test_html_time_range_display():
    """Test HTML time range display logic.
    
    Expected:
    - Show only when both start_time and end_time are non-empty
    - Don't show when only one is present
    - Don't show when both are empty
    """
    row_with = ["head", "8:00", "Day", 1, "09:00", "17:00"]
    html = report_utils.format_html_time_range(row_with)
    assert "09:00 - 17:00" in html, f"Time range should be visible: {html}"
    assert "<span" in html, f"Should have span tag: {html}"
    
    row_start_only = ["head", "8:00", "Day", 1, "09:00", ""]
    html = report_utils.format_html_time_range(row_start_only)
    assert html == "", f"No span when end time is empty: {html}"
    
    row_end_only = ["head", "8:00", "Day", 1, "", "17:00"]
    html = report_utils.format_html_time_range(row_end_only)
    assert html == "", f"No span when start time is empty: {html}"
    
    row_none = ["head", "8:00", "#work", 1]
    html = report_utils.format_html_time_range(row_none)
    assert html == "", f"No span when no times: {html}"
    
    print(f"  OK HTML time range: shown only when both times present")


def test_pdf_time_range_display():
    """Test PDF time range display logic.
    
    Expected:
    - Show only when both start_time and end_time are non-empty
    - Format: "  HH:MM - HH:MM"
    """
    row_with = ["head", "8:00", "Day", 1, "09:00", "17:00"]
    should_show, time_text = report_utils.format_pdf_time_range(row_with)
    assert should_show == True, "Should show time range when both times present"
    assert "09:00 - 17:00" in time_text, f"Time text should contain range: {time_text}"
    assert time_text.startswith("  "), f"Time text should have leading spaces: '{time_text}'"
    
    row_no_time = ["head", "3:00", "#work", 1]
    should_show, time_text = report_utils.format_pdf_time_range(row_no_time)
    assert should_show == False, "Should not show time range when no times"
    assert time_text == "", f"Time text should be empty: '{time_text}'"
    
    row_partial = ["head", "8:00", "Day", 1, "09:00", ""]
    should_show, time_text = report_utils.format_pdf_time_range(row_partial)
    assert should_show == False, "Should not show time range when only one time present"
    
    print(f"  OK PDF time range: correct conditional display")


def test_group_method_none_with_day_period():
    """Test group_method='none' with group_period='day'.
    
    Expected:
    - All records in one "hidden" group
    - Time range covers all records in each day
    """
    base_ts = 1776936000
    
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
    
    rows = report_utils.generate_report_rows(
        records,
        group_method="none",
        group_period="day",
        showrecords=False,
        dt=dt,
    )
    
    head_rows = [r for r in rows if r[0] == "head" and r[2] != "Total"]
    
    assert len(head_rows) == 1, f"Expected 1 day group, got {len(head_rows)}"
    
    row = head_rows[0]
    assert row[4], f"start_time should not be empty"
    assert row[5], f"end_time should not be empty"
    
    expected_start = dt.time2localstr(base_ts).split(" ")[1][:5]
    expected_end = dt.time2localstr(base_ts + 10800).split(" ")[1][:5]
    
    assert row[4] == expected_start, f"start_time should be '{expected_start}', got '{row[4]}'"
    assert row[5] == expected_end, f"end_time should be '{expected_end}', got '{row[5]}'"
    
    print(f"  OK group_method='none' with day period: time range covers all records")


def test_records_out_of_order():
    """Test records added out of chronological order.
    
    Expected:
    - min_t1 = earliest t1 regardless of order
    - max_t2 = latest t2 regardless of order
    """
    base_ts = 1776936000
    
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
        }
    ]
    
    rows = report_utils.generate_report_rows(
        records,
        group_method="tagz",
        group_period="day",
        showrecords=False,
        dt=dt,
    )
    
    head_rows = [r for r in rows if r[0] == "head" and r[2] != "Total"]
    
    assert len(head_rows) == 1, f"Expected 1 day group, got {len(head_rows)}"
    
    row = head_rows[0]
    
    expected_start = dt.time2localstr(base_ts).split(" ")[1][:5]
    expected_end = dt.time2localstr(base_ts + 14400).split(" ")[1][:5]
    
    assert row[4] == expected_start, f"start_time should be '{expected_start}', got '{row[4]}'"
    assert row[5] == expected_end, f"end_time should be '{expected_end}', got '{row[5]}'"
    
    print(f"  OK Out-of-order records: start={row[4]}, end={row[5]} (correct min/max)")


def test_single_record_day():
    """Test single record in a day.
    
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
    
    rows = report_utils.generate_report_rows(
        records,
        group_method="tagz",
        group_period="day",
        showrecords=False,
        dt=dt,
    )
    
    head_rows = [r for r in rows if r[0] == "head" and r[2] != "Total"]
    
    assert len(head_rows) == 1, f"Expected 1 day group, got {len(head_rows)}"
    
    row = head_rows[0]
    
    expected_start = dt.time2localstr(base_ts + 3600).split(" ")[1][:5]
    expected_end = dt.time2localstr(base_ts + 7200).split(" ")[1][:5]
    
    assert row[4] == expected_start, f"start_time should be '{expected_start}', got '{row[4]}'"
    assert row[5] == expected_end, f"end_time should be '{expected_end}', got '{row[5]}'"
    
    print(f"  OK Single record day: start={row[4]}, end={row[5]}")


def test_group_method_ds():
    """Test group_method='ds' (group by description).
    
    Expected:
    - Records grouped by description
    - Time range calculated correctly when period grouping is enabled
    """
    base_ts = 1776936000
    
    records = [
        {
            "key": "rec1",
            "t1": base_ts,  # 12:00
            "t2": base_ts + 3600,  # 13:00
            "duration": 3600,
            "tagz": "#work",
            "ds": "Task A"
        },
        {
            "key": "rec2",
            "t1": base_ts + 7200,  # 14:00
            "t2": base_ts + 10800,  # 15:00
            "duration": 3600,
            "tagz": "#work",
            "ds": "Task B"
        },
        {
            "key": "rec3",
            "t1": base_ts + 1800,  # 12:30
            "t2": base_ts + 5400,  # 13:30
            "duration": 3600,
            "tagz": "#work",
            "ds": "Task A"
        }
    ]
    
    rows = report_utils.generate_report_rows(
        records,
        group_method="ds",
        group_period="day",
        showrecords=False,
        dt=dt,
    )
    
    head_rows = [r for r in rows if r[0] == "head" and r[2] != "Total"]
    
    assert len(head_rows) == 2, f"Expected 2 groups (Task A and Task B), got {len(head_rows)}"
    
    for row in head_rows:
        assert row[4], f"Each day group should have start_time: {row}"
        assert row[5], f"Each day group should have end_time: {row}"
    
    print(f"  OK group_method='ds': {len(head_rows)} groups, all have time ranges")


def test_month_grouping():
    """Test group_period='month'.
    
    Expected:
    - Records grouped by month
    - min_t1/max_t2 calculated correctly for the month
    """
    base_ts_april = 1776892800  # 2026-04-22
    base_ts_may = 1779484800  # 2026-05-22 (approx)
    
    records = [
        {
            "key": "rec1",
            "t1": base_ts_april + 12 * 3600,
            "t2": base_ts_april + 13 * 3600,
            "duration": 3600,
            "tagz": "#work",
            "ds": "April work"
        },
        {
            "key": "rec2",
            "t1": base_ts_april + 14 * 3600,
            "t2": base_ts_april + 16 * 3600,
            "duration": 7200,
            "tagz": "#work",
            "ds": "April more"
        }
    ]
    
    rows = report_utils.generate_report_rows(
        records,
        group_method="tagz",
        group_period="month",
        showrecords=False,
        dt=dt,
    )
    
    head_rows = [r for r in rows if r[0] == "head" and r[2] != "Total"]
    
    assert len(head_rows) == 1, f"Expected 1 month group, got {len(head_rows)}"
    
    row = head_rows[0]
    assert row[4], f"Month group should have start_time"
    assert row[5], f"Month group should have end_time"
    
    expected_start = dt.time2localstr(base_ts_april + 12 * 3600).split(" ")[1][:5]
    expected_end = dt.time2localstr(base_ts_april + 16 * 3600).split(" ")[1][:5]
    
    assert row[4] == expected_start, f"start_time should be '{expected_start}', got '{row[4]}'"
    assert row[5] == expected_end, f"end_time should be '{expected_end}', got '{row[5]}'"
    
    print(f"  OK Month grouping: start={row[4]}, end={row[5]}")


if __name__ == "__main__":
    run_tests(globals())
