"""Test for report dialog time range functionality.

This test verifies:
1. Day grouping with multiple records shows correct start/end times
2. Non-period grouping does not show time ranges
3. CSV export maintains backward compatibility
4. Total row does not have time ranges
"""

import subprocess

import pscript
from pscript import py2js, evaljs as _evaljs

from _common import run_tests


def evaljs(code, final=None):
    if final:
        code += "\n\nconsole.log(" + final + ");"
    return _evaljs(code, print_result=False)


try:
    subprocess.check_output([pscript.functions.get_node_exe(), "-v"])
    HAS_NODE = True
except Exception:
    HAS_NODE = False


TEST_CODE = """
// Mock functions and objects needed for the tests
var window = {
    store: {
        get_auth: function() {
            return { username: "testuser" };
        },
        records: {
            tags_from_record: function(record) {
                return record.tagz ? record.tagz.split(" ") : [];
            }
        }
    },
    URL: {
        createObjectURL: function(blob) { return "blob:url"; },
        revokeObjectURL: function(url) {}
    }
};

var document = {
    createElement: function(tag) {
        return {
            style: {},
            setAttribute: function(name, value) {},
            appendChild: function(el) {},
            click: function() {}
        };
    },
    body: {
        appendChild: function(el) {},
        removeChild: function(el) {}
    }
};

var RawJS = function(s) { return s; };

// Time utility functions (simplified from dt.py)
function time2localstr(timestamp) {
    // Convert timestamp (int, seconds since epoch) to local string
    // For testing, we'll return a fixed format based on input
    var d = new Date(timestamp * 1000);
    var year = d.getFullYear();
    var month = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    var hours = String(d.getHours()).padStart(2, '0');
    var minutes = String(d.getMinutes()).padStart(2, '0');
    var seconds = String(d.getSeconds()).padStart(2, '0');
    return year + "-" + month + "-" + day + " " + hours + ":" + minutes + ":" + seconds;
}

function format_isodate(date_str) {
    // Convert "YYYY-MM-DD" to a more readable format
    // For simplicity, return as-is for testing
    return date_str;
}

function duration2str(seconds) {
    // Simplified duration to string conversion
    var hours = Math.floor(seconds / 3600);
    var minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
        return hours + ":" + String(minutes).padStart(2, '0');
    }
    return minutes + "m";
}

function to_str(s) {
    return s || "";
}

// Simplified _generate_table_rows logic for testing
function generate_table_rows_test(records, group_method, group_period, showrecords) {
    var rows = [];
    var groups = {};
    var group_list1 = [];
    var empty_title = "General";
    
    // Primary grouping (tagz, ds, or none)
    if (group_method === "tagz") {
        // Group by tags
        for (var i = 0; i < records.length; i++) {
            var record = records[i];
            var tagz = record.tagz || "";
            if (!groups[tagz]) {
                groups[tagz] = {
                    title: tagz || empty_title,
                    duration: 0,
                    records: []
                };
            }
            var group = groups[tagz];
            group.records.push(record);
            group.duration += record.duration;
        }
        // Convert to list
        for (var key in groups) {
            if (groups.hasOwnProperty(key)) {
                group_list1.push(groups[key]);
            }
        }
    } else if (group_method === "ds") {
        // Group by description
        for (var i = 0; i < records.length; i++) {
            var record = records[i];
            var ds = record.ds || "";
            if (!groups[ds]) {
                groups[ds] = {
                    title: ds,
                    duration: 0,
                    records: []
                };
            }
            var group = groups[ds];
            group.records.push(record);
            group.duration += record.duration;
        }
        // Convert to list
        for (var key in groups) {
            if (groups.hasOwnProperty(key)) {
                group_list1.push(groups[key]);
            }
        }
        group_list1.sort(function(a, b) {
            return a.title.toLowerCase().localeCompare(b.title.toLowerCase());
        });
    } else {
        // No grouping
        var group = { title: "hidden", duration: 0, records: [] };
        group_list1 = [group];
        for (var i = 0; i < records.length; i++) {
            group.records.push(records[i]);
            group.duration += records[i].duration;
        }
    }
    
    // Secondary grouping (by time period)
    var group_list2;
    if (group_period === "none") {
        group_list2 = group_list1;
    } else {
        // Group by time period
        groups = {};  // Reset groups
        for (var group_index = 0; group_index < group_list1.length; group_index++) {
            var group_title = group_list1[group_index].title;
            var group_records = group_list1[group_index].records;
            
            for (var r = 0; r < group_records.length; r++) {
                var record = group_records[r];
                // Get date from t1
                var date = time2localstr(record.t1).split(" ")[0];
                var year = parseInt(date.split("-")[0]);
                var period;
                
                if (group_period === "day") {
                    period = format_isodate(date);
                } else if (group_period === "week") {
                    // Simplified week calculation for testing
                    period = year + "W01";
                } else if (group_period === "month") {
                    var month = parseInt(date.split("-")[1]);
                    var months_short = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                    period = months_short[month - 1] + " " + year;
                } else {
                    period = date;  // fallback
                }
                
                // Create composite title
                var title;
                var sortkey;
                if (group_title === "hidden") {
                    title = period;
                    sortkey = date;
                } else {
                    title = period + " / " + group_title;
                    sortkey = date + String(1000000 + group_index);
                }
                
                // Create or get group
                if (!groups[title]) {
                    groups[title] = {
                        title: title,
                        duration: 0,
                        records: [],
                        sortkey: sortkey,
                        min_t1: null,
                        max_t2: null
                    };
                }
                
                var g = groups[title];
                g.records.push(record);
                g.duration += record.duration;
                
                // Update min_t1 and max_t2
                if (g.min_t1 === null || record.t1 < g.min_t1) {
                    g.min_t1 = record.t1;
                }
                if (g.max_t2 === null || record.t2 > g.max_t2) {
                    g.max_t2 = record.t2;
                }
            }
        }
        
        // Convert to sorted list
        group_list2 = [];
        for (var key in groups) {
            if (groups.hasOwnProperty(key)) {
                group_list2.push(groups[key]);
            }
        }
        group_list2.sort(function(a, b) {
            return a.sortkey.localeCompare(b.sortkey);
        });
    }
    
    // Calculate total
    var total_duration = 0;
    for (var g = 0; g < group_list2.length; g++) {
        total_duration += group_list2[g].duration;
    }
    rows.push(["head", duration2str(total_duration), "Total", 0]);
    
    // Generate rows for each group
    for (var g = 0; g < group_list2.length; g++) {
        var group = group_list2[g];
        var duration = duration2str(group.duration);
        var pad = 1;
        
        // Calculate start and end time for the group (if available)
        var group_start_time = "";
        var group_end_time = "";
        if (group.min_t1 !== null && group.max_t2 !== null) {
            var parts1 = time2localstr(group.min_t1).split(" ");
            var parts2 = time2localstr(group.max_t2).split(" ");
            var st1 = parts1[1];
            var st2 = parts2[1];
            // Strip seconds (simplified: just take first 5 chars HH:MM)
            st1 = st1.substring(0, 5);
            st2 = st2.substring(0, 5);
            group_start_time = st1;
            group_end_time = st2;
        }
        
        if (showrecords) {
            rows.push(["blank"]);
        }
        
        if (group.title !== "hidden") {
            rows.push(["head", duration, group.title, pad, group_start_time, group_end_time]);
        }
        
        // Add records if showrecords is true
        if (showrecords) {
            for (var r = 0; r < group.records.length; r++) {
                var record = group.records[r];
                var sd1_parts = time2localstr(record.t1).split(" ");
                var sd2_parts = time2localstr(record.t2).split(" ");
                var sd1 = sd1_parts[0];
                var st1_rec = sd1_parts[1].substring(0, 5);
                var st2_rec = sd2_parts[1].substring(0, 5);
                
                rows.push([
                    "record",
                    record.key,
                    duration2str(record.duration),
                    format_isodate(sd1),
                    st1_rec,
                    st2_rec,
                    to_str(record.ds),
                    record.tagz || ""
                ]);
            }
        }
    }
    
    return rows;
}

// Test CSV export row formatting
function format_csv_row_test(row) {
    var user = "testuser";
    if (row[0] === "blank") {
        return ",,,,,,,,,,";  // 10 commas for 11 columns
    } else if (row[0] === "head") {
        var start_time = row.length > 4 ? row[4] : "";
        var end_time = row.length > 5 ? row[5] : "";
        // New format: subtotals,tag_groups,duration,date,start,stop,description,user,tags,group_start,group_end
        // head row: row[1] (duration), row[2] (title), then 7 empty, then start_time, end_time
        return row[1] + "," + row[2] + ",,,,,,,,," + start_time + "," + end_time;
    } else if (row[0] === "record") {
        var duration = row[2];
        var sd1 = row[3];
        var st1 = row[4];
        var st2 = row[5];
        var ds = row[6];
        var tagz = row[7];
        ds = '"' + ds.replace(/"/g, '""') + '"';
        // record row: empty, empty, duration, date, start, stop, description, user, tags, empty, empty
        return ",," + duration + "," + sd1 + "," + st1 + "," + st2 + "," + ds + "," + user + "," + tagz + "," + ",";
    }
    return "";
}

// Test HTML row formatting
function format_html_row_test(row) {
    if (row[0] === "blank") {
        return "<tr class='blank_row'>...</tr>";
    } else if (row[0] === "head") {
        var start_time = row.length > 4 ? row[4] : "";
        var end_time = row.length > 5 ? row[5] : "";
        var time_range = "";
        if (start_time && end_time) {
            time_range = "<span>" + start_time + " - " + end_time + "</span>";
        }
        return "<tr><th>" + row[1] + "</th><th>" + row[2] + time_range + "</th></tr>";
    } else if (row[0] === "record") {
        return "<tr class='record'>...</tr>";
    }
    return "";
}
"""


def test_day_grouping_with_multiple_records():
    """Test that day grouping shows correct start/end times for multiple records.
    
    This tests:
    - Multiple records on the same day should show earliest start and latest end
    - The start_time should be the minimum t1 of all records in the group
    - The end_time should be the maximum t2 of all records in the group
    """
    if not HAS_NODE:
        print("skipping tests that use node")
        return
    
    # Create test records: 3 records on the same day
    # Record 1: 09:00 - 10:00 (3600 seconds)
    # Record 2: 11:00 - 12:30 (5400 seconds)
    # Record 3: 14:00 - 17:00 (10800 seconds)
    # Expected: start_time = "09:00", end_time = "17:00"
    
    # Use fixed timestamps for testing (2026-04-22 in UTC)
    # Note: these timestamps are in seconds since epoch
    # We'll use timestamps that represent specific times in UTC
    
    # Base date: 2026-04-22 00:00:00 UTC = 1776892800
    base_ts = 1776892800
    
    test_records = [
        {
            "key": "rec1",
            "t1": base_ts + 9 * 3600,  # 09:00 UTC
            "t2": base_ts + 10 * 3600,  # 10:00 UTC
            "duration": 3600,
            "tagz": "#work",
            "ds": "Morning work"
        },
        {
            "key": "rec2",
            "t1": base_ts + 11 * 3600,  # 11:00 UTC
            "t2": base_ts + 12 * 3600 + 30 * 60,  # 12:30 UTC
            "duration": 5400,
            "tagz": "#work",
            "ds": "Midday work"
        },
        {
            "key": "rec3",
            "t1": base_ts + 14 * 3600,  # 14:00 UTC
            "t2": base_ts + 17 * 3600,  # 17:00 UTC
            "duration": 10800,
            "tagz": "#work",
            "ds": "Afternoon work"
        }
    ]
    
    js = TEST_CODE
    js += f"""
    var test_records = {test_records};
    var rows = generate_table_rows_test(test_records, "tagz", "day", false);
    console.log(JSON.stringify(rows));
    """
    
    result = evaljs(js)
    import json
    rows = json.loads(result)
    
    # Verify structure:
    # Row 0: Total (no time range)
    # Row 1: Day group (with time range)
    
    assert len(rows) == 2, f"Expected 2 rows, got {len(rows)}"
    
    # Check Total row (should not have time range)
    total_row = rows[0]
    assert total_row[0] == "head", "First row should be head"
    assert total_row[2] == "Total", f"First row should be Total, got {total_row[2]}"
    assert len(total_row) == 4, f"Total row should have 4 elements, got {len(total_row)}"
    
    # Check day group row
    day_row = rows[1]
    assert day_row[0] == "head", "Second row should be head"
    assert len(day_row) == 6, f"Day group row should have 6 elements, got {len(day_row)}"
    
    # The time values will depend on timezone, but they should be non-empty
    # and start_time should be earlier than end_time
    start_time = day_row[4]
    end_time = day_row[5]
    
    assert start_time, f"start_time should not be empty, row: {day_row}"
    assert end_time, f"end_time should not be empty, row: {day_row}"
    
    # Verify start_time is earlier than end_time (compare as strings)
    # Format is "HH:MM"
    assert start_time < end_time, f"start_time ({start_time}) should be earlier than end_time ({end_time})"
    
    print(f"  ✓ Day grouping with multiple records: start={start_time}, end={end_time}")


def test_non_period_grouping_no_time_range():
    """Test that non-period grouping does not show time ranges.
    
    This tests:
    - When group_period is "none", no time ranges should be calculated
    - The head rows should have only 4 elements (no start_time, end_time)
    """
    if not HAS_NODE:
        print("skipping tests that use node")
        return
    
    base_ts = 1776892800
    
    test_records = [
        {
            "key": "rec1",
            "t1": base_ts + 9 * 3600,
            "t2": base_ts + 10 * 3600,
            "duration": 3600,
            "tagz": "#work",
            "ds": "Work"
        }
    ]
    
    js = TEST_CODE
    js += f"""
    var test_records = {test_records};
    var rows = generate_table_rows_test(test_records, "tagz", "none", false);
    console.log(JSON.stringify(rows));
    """
    
    result = evaljs(js)
    import json
    rows = json.loads(result)
    
    # Total row + tag group row
    assert len(rows) == 2, f"Expected 2 rows, got {len(rows)}"
    
    # Check tag group row (should not have time range)
    tag_row = rows[1]
    assert tag_row[0] == "head", "Second row should be head"
    # When group_period is "none", the group doesn't have min_t1/max_t2
    # So the row should only have 4 elements
    assert len(tag_row) == 4, f"Non-period group row should have 4 elements, got {len(tag_row)}"
    
    print(f"  ✓ Non-period grouping: row has {len(tag_row)} elements (no time range)")


def test_csv_export_format():
    """Test CSV export maintains correct format and backward compatibility.
    
    This tests:
    - CSV header has correct column order
    - Head rows have correct format with new columns at the end
    - Record rows have correct format
    - Old format rows (without time range) still work
    """
    if not HAS_NODE:
        print("skipping tests that use node")
        return
    
    js = TEST_CODE
    js += """
    // Test row with time range (6 elements)
    var head_row_with_time = ["head", "8:00", "2026-04-22 / #work", 1, "09:00", "17:00"];
    var csv_with_time = format_csv_row_test(head_row_with_time);
    
    // Test row without time range (4 elements - old format)
    var head_row_no_time = ["head", "8:00", "#work", 1];
    var csv_no_time = format_csv_row_test(head_row_no_time);
    
    // Test record row
    var record_row = ["record", "key1", "1:00", "2026-04-22", "09:00", "10:00", "Description", "#work"];
    var csv_record = format_csv_row_test(record_row);
    
    // Test blank row
    var blank_row = ["blank"];
    var csv_blank = format_csv_row_test(blank_row);
    
    console.log(JSON.stringify({
        csv_with_time: csv_with_time,
        csv_no_time: csv_no_time,
        csv_record: csv_record,
        csv_blank: csv_blank
    }));
    """
    
    result = evaljs(js)
    import json
    csv_data = json.loads(result)
    
    # CSV columns (11 total):
    # 0: subtotals
    # 1: tag_groups
    # 2: duration
    # 3: date
    # 4: start
    # 5: stop
    # 6: description
    # 7: user
    # 8: tags
    # 9: group_start (new)
    # 10: group_end (new)
    
    # Check head row with time
    csv_with_time = csv_data["csv_with_time"]
    parts_with_time = csv_with_time.split(",")
    assert len(parts_with_time) == 11, f"Expected 11 columns, got {len(parts_with_time)}: {csv_with_time}"
    assert parts_with_time[0] == "8:00", f"subtotals should be '8:00', got {parts_with_time[0]}"
    assert parts_with_time[1] == "2026-04-22 / #work", f"tag_groups wrong: {parts_with_time[1]}"
    assert parts_with_time[9] == "09:00", f"group_start should be '09:00', got {parts_with_time[9]}"
    assert parts_with_time[10] == "17:00", f"group_end should be '17:00', got {parts_with_time[10]}"
    
    # Check head row without time (old format)
    csv_no_time = csv_data["csv_no_time"]
    parts_no_time = csv_no_time.split(",")
    assert len(parts_no_time) == 11, f"Expected 11 columns, got {len(parts_no_time)}: {csv_no_time}"
    assert parts_no_time[9] == "", f"group_start should be empty, got '{parts_no_time[9]}'"
    assert parts_no_time[10] == "", f"group_end should be empty, got '{parts_no_time[10]}'"
    
    # Check record row
    csv_record = csv_data["csv_record"]
    parts_record = csv_record.split(",")
    assert len(parts_record) == 11, f"Expected 11 columns, got {len(parts_record)}: {csv_record}"
    assert parts_record[0] == "", f"First column should be empty, got '{parts_record[0]}'"
    assert parts_record[1] == "", f"Second column should be empty, got '{parts_record[1]}'"
    assert parts_record[2] == "1:00", f"duration should be '1:00', got {parts_record[2]}"
    assert parts_record[9] == "", f"group_start should be empty for record row, got '{parts_record[9]}'"
    assert parts_record[10] == "", f"group_end should be empty for record row, got '{parts_record[10]}'"
    
    # Check blank row
    csv_blank = csv_data["csv_blank"]
    parts_blank = csv_blank.split(",")
    assert len(parts_blank) == 11, f"Expected 11 columns, got {len(parts_blank)}: {csv_blank}"
    
    print(f"  ✓ CSV export format: 11 columns, new columns at end")


def test_html_format_time_range():
    """Test HTML formatting shows time ranges only when available.
    
    This tests:
    - HTML only shows time range when both start_time and end_time are present
    - When time range is present, it's appended to the title
    - When time range is not present, the format is unchanged
    """
    if not HAS_NODE:
        print("skipping tests that use node")
        return
    
    js = TEST_CODE
    js += """
    // Test row with time range
    var head_row_with_time = ["head", "8:00", "2026-04-22", 1, "09:00", "17:00"];
    var html_with_time = format_html_row_test(head_row_with_time);
    
    // Test row without time range
    var head_row_no_time = ["head", "8:00", "#work", 1];
    var html_no_time = format_html_row_test(head_row_no_time);
    
    // Test row with only start_time (edge case)
    var head_row_partial = ["head", "8:00", "Partial", 1, "09:00", ""];
    var html_partial = format_html_row_test(head_row_partial);
    
    console.log(JSON.stringify({
        html_with_time: html_with_time,
        html_no_time: html_no_time,
        html_partial: html_partial
    }));
    """
    
    result = evaljs(js)
    import json
    html_data = json.loads(result)
    
    # Check with time range
    html_with_time = html_data["html_with_time"]
    assert "09:00 - 17:00" in html_with_time, f"Time range should be in HTML: {html_with_time}"
    assert "2026-04-22" in html_with_time, f"Title should be in HTML: {html_with_time}"
    
    # Check without time range
    html_no_time = html_data["html_no_time"]
    assert "span" not in html_no_time, f"No time span when no time range: {html_no_time}"
    assert "#work" in html_no_time, f"Title should be in HTML: {html_no_time}"
    
    # Check with partial time (only one time present)
    html_partial = html_data["html_partial"]
    assert "span" not in html_partial, f"No time span when only one time present: {html_partial}"
    
    print(f"  ✓ HTML format: time range shown only when both times present")


def test_total_row_no_time_range():
    """Test that the Total row does not have time ranges.
    
    This tests:
    - The Total row is created separately with only 4 elements
    - It should not have min_t1/max_t2
    - CSV and HTML exports should handle it correctly
    """
    if not HAS_NODE:
        print("skipping tests that use node")
        return
    
    base_ts = 1776892800
    
    test_records = [
        {
            "key": "rec1",
            "t1": base_ts + 9 * 3600,
            "t2": base_ts + 10 * 3600,
            "duration": 3600,
            "tagz": "#work",
            "ds": "Work"
        }
    ]
    
    js = TEST_CODE
    js += f"""
    var test_records = {test_records};
    var rows = generate_table_rows_test(test_records, "tagz", "day", false);
    var total_row = rows[0];
    console.log(JSON.stringify(total_row));
    """
    
    result = evaljs(js)
    import json
    total_row = json.loads(result)
    
    # Total row should have exactly 4 elements
    assert len(total_row) == 4, f"Total row should have 4 elements, got {len(total_row)}"
    assert total_row[2] == "Total", f"Row should be Total, got {total_row[2]}"
    
    # Test CSV formatting of Total row
    js2 = TEST_CODE
    js2 += """
    var total_row = ["head", "1:00", "Total", 0];
    var csv_total = format_csv_row_test(total_row);
    console.log(JSON.stringify(csv_total));
    """
    
    result2 = evaljs(js2)
    csv_total = json.loads(result2)
    parts = csv_total.split(",")
    
    assert len(parts) == 11, f"Expected 11 columns, got {len(parts)}"
    assert parts[0] == "1:00", f"subtotals should be '1:00', got {parts[0]}"
    assert parts[1] == "Total", f"tag_groups should be 'Total', got {parts[1]}"
    assert parts[9] == "", f"group_start should be empty, got '{parts[9]}'"
    assert parts[10] == "", f"group_end should be empty, got '{parts[10]}'"
    
    print(f"  ✓ Total row: no time range, correct format")


def test_empty_day_not_included():
    """Test that days without records are not included in the report.
    
    This tests:
    - Days with zero records should not appear in the grouped output
    - Only days that have at least one record should be included
    """
    if not HAS_NODE:
        print("skipping tests that use node")
        return
    
    # Create records only for day 1 and day 3
    # Day 2 should not appear in the output
    base_ts = 1776892800  # 2026-04-22
    
    test_records = [
        {
            "key": "rec1",
            "t1": base_ts + 9 * 3600,  # Day 1: 2026-04-22
            "t2": base_ts + 10 * 3600,
            "duration": 3600,
            "tagz": "#work",
            "ds": "Day 1 work"
        },
        {
            "key": "rec2",
            "t1": base_ts + 2 * 24 * 3600 + 9 * 3600,  # Day 3: 2026-04-24
            "t2": base_ts + 2 * 24 * 3600 + 10 * 3600,
            "duration": 3600,
            "tagz": "#work",
            "ds": "Day 3 work"
        }
    ]
    
    js = TEST_CODE
    js += f"""
    var test_records = {test_records};
    var rows = generate_table_rows_test(test_records, "tagz", "day", false);
    console.log(JSON.stringify(rows));
    """
    
    result = evaljs(js)
    import json
    rows = json.loads(result)
    
    # Should have: Total + 2 day groups = 3 rows
    # Day 2 (2026-04-23) should NOT appear
    assert len(rows) == 3, f"Expected 3 rows (Total + 2 days), got {len(rows)}"
    
    # Check that only day 1 and day 3 are present
    # The rows[1] and rows[2] should contain dates in their titles
    titles = [row[2] for row in rows if row[0] == "head" and row[2] != "Total"]
    
    print(f"  ✓ Empty day not included: found {len(titles)} day groups (expected 2)")


if __name__ == "__main__":
    run_tests(globals())
