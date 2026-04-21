"""
Test pomodoro preserve on record change functionality.

This module tests the actual implementation code paths by:
1. Checking the actual code logic in the source files
2. Verifying that certain code paths exist or don't exist
3. Testing the parts that can be tested in pure Python

Note: Since the actual PScript code runs in the browser, we verify
the implementation by checking the source code structure and logic.
"""

import os
from _common import run_tests


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_source_file(relative_path):
    """Get the full path to a source file."""
    return os.path.join(PROJECT_ROOT, *relative_path.split("/"))


def read_source_file(relative_path):
    """Read a source file and return its contents."""
    path = get_source_file(relative_path)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_utils_has_pomodoro_preserve_setting():
    """Test that SimpleSettings has the pomodoro_preserve_on_record_change setting.
    
    This tests the actual Python implementation in utils.py.
    """
    from timetagger.app.utils import SimpleSettings

    settings = SimpleSettings()

    assert "pomodoro_preserve_on_record_change" in settings._local_keys

    assert settings._local_keys["pomodoro_preserve_on_record_change"] is False

    assert settings.get("pomodoro_preserve_on_record_change") is False


def test_dialogs_record_submit_lmode_logic():
    """Test that RecordDialog.submit() correctly handles different lmode values.
    
    Verifies the actual implementation in dialogs.py:
    - Only 'start' and 'stop' modes can affect pomodoro
    - 'edit' and 'new' modes should NOT affect pomodoro
    """
    dialogs_source = read_source_file("timetagger/app/dialogs.py")

    assert 'if self._lmode == "start":' in dialogs_source
    assert 'elif self._lmode == "stop":' in dialogs_source
    assert 'if self._lmode == "start" or self._lmode == "edit":' not in dialogs_source
    assert 'elif self._lmode == "edit":' not in dialogs_source
    assert 'elif self._lmode == "new":' not in dialogs_source

    submit_section = extract_method_body(dialogs_source, "def submit(self):", "def resume_record")

    assert "lmode" in submit_section.lower()
    assert "start_work()" in submit_section
    assert "stop()" in submit_section

    start_condition = 'if self._lmode == "start":' in submit_section
    stop_condition = 'elif self._lmode == "stop":' in submit_section
    assert start_condition, "Expected 'start' condition in submit()"
    assert stop_condition, "Expected 'stop' condition in submit()"


def test_dialogs_record_edit_mode_does_not_affect_pomodoro():
    """Test that edit mode does NOT trigger pomodoro start/stop.
    
    Verification:
    1. The submit() method only checks for 'start' and 'stop' lmode
    2. There's no 'edit' or 'new' condition that would call pomodoro methods
    3. The resume_record() method is separate from edit mode
    """
    dialogs_source = read_source_file("timetagger/app/dialogs.py")

    submit_body = extract_method_body(dialogs_source, "def submit(self):", "def resume_record")

    submit_has_edit = 'lmode == "edit"' in submit_body
    submit_has_new = 'lmode == "new"' in submit_body

    assert not submit_has_edit, "Edit mode should not have special handling in submit()"
    assert not submit_has_new, "New mode should not have special handling in submit()"

    set_mode_body = extract_method_body(dialogs_source, "def _set_mode", "def _ds_input")

    assert 'lmode == "edit"' in set_mode_body

    edit_mode_buttons = 'lmode == "edit"' in set_mode_body and 'lmode == "start"' in set_mode_body
    assert edit_mode_buttons, "Edit mode should be a distinct mode from start"


def test_front_nav_and_select_actions_do_not_affect_pomodoro():
    """Test that nav_ and select_ actions do NOT affect pomodoro state.
    
    Verification:
    1. nav_ actions (navigation, zoom, snap) are handled separately
    2. select_ actions (tag selection) are handled separately  
    3. These sections do NOT contain any pomodoro_dialog calls
    """
    front_source = read_source_file("timetagger/app/front.py")

    on_click_body = extract_method_body(front_source, "def _on_click", "class RecordsWidget")

    nav_section = extract_section(on_click_body, 'elif action.startswith("nav_"):', 'elif action.startswith')
    select_section = extract_section(on_click_body, 'elif action.startswith("select_"):', "class RecordsWidget")

    assert "pomodoro" not in nav_section.lower(), "nav_ actions should not affect pomodoro"
    assert "pomodoro" not in select_section.lower(), "select_ actions should not affect pomodoro"
    assert "start_work" not in nav_section
    assert "stop()" not in nav_section

    assert "record_stopall" in on_click_body
    assert "pomodoro_dialog.stop" in on_click_body


def test_dialogs_pomodoro_storage_persistence_logic():
    """Test that pomodoro state persistence only saves work/break states.
    
    Verification:
    1. _save_state_to_storage() checks if state is in ("work", "break")
    2. pre-work/pre-break states should clear storage
    3. _clear_state_from_storage() is called when appropriate
    """
    dialogs_source = read_source_file("timetagger/app/dialogs.py")

    save_state_body = extract_method_body(dialogs_source, "def _save_state_to_storage", "def _clear_state_from_storage")

    assert 'if state in ("work", "break"):' in save_state_body

    assert "_clear_state_from_storage()" in save_state_body

    clear_state_body = extract_method_body(dialogs_source, "def _clear_state_from_storage", "def _load_state_from_storage")

    assert "localStorage.removeItem" in clear_state_body

    init_state_body = extract_method_body(dialogs_source, "def _init_state", "def _save_state_to_storage")

    assert "pomodoro_enabled" in init_state_body
    assert "pomodoro_preserve_on_record_change" in init_state_body


def test_dialogs_settings_callbacks_clear_storage():
    """Test that turning off pomodoro settings clears stored state.
    
    Verification:
    1. _on_pomodoro_check() clears storage when pomodoro_enabled is turned off
    2. _on_pomodoro_preserve_check() clears storage when preserve is turned off
    """
    dialogs_source = read_source_file("timetagger/app/dialogs.py")

    pomo_check_body = extract_method_body(dialogs_source, "def _on_pomodoro_check", "def _on_pomodoro_preserve_check")

    assert "_clear_state_from_storage()" in pomo_check_body
    assert "if not pomo_enabled:" in pomo_check_body

    pomo_preserve_check_body = extract_method_body(dialogs_source, "def _on_pomodoro_preserve_check", "def _on_stopwatch_check")

    assert "_clear_state_from_storage()" in pomo_preserve_check_body
    assert "if not pomo_preserve:" in pomo_preserve_check_body


def test_dialogs_pomodoro_stop_method():
    """Test that PomodoroDialog.stop() sets state to pre-work.
    
    Verification:
    1. stop() calls _set_state("pre-work")
    2. pre-work state will trigger _clear_state_from_storage()
    """
    dialogs_source = read_source_file("timetagger/app/dialogs.py")

    stop_body = extract_method_body(dialogs_source, "def stop(self):", "def _init_state")

    assert '_set_state("pre-work")' in stop_body


def test_complete_workflow_code_structure():
    """Test that the complete workflow code structure is correct.
    
    Verifies all the key components are in place:
    1. RecordDialog.submit() has preserve logic for start/stop
    2. RecordDialog.resume_record() has preserve logic
    3. Front._on_click() has preserve logic for record_stopall
    4. PomodoroDialog has persistence and cleanup methods
    """
    dialogs_source = read_source_file("timetagger/app/dialogs.py")
    front_source = read_source_file("timetagger/app/front.py")

    submit_body = extract_method_body(dialogs_source, "def submit(self):", "def resume_record")

    assert "pomodoro_preserve_on_record_change" in submit_body
    assert "preserve = window.simplesettings.get" in submit_body
    assert "is_running = current_pomo_state" in submit_body
    assert "if not preserve or not is_running:" in submit_body
    assert "if not preserve:" in submit_body

    resume_body = extract_method_body(dialogs_source, "def resume_record", "def send_notification")

    assert "pomodoro_preserve_on_record_change" in resume_body
    assert "if not preserve or not is_running:" in resume_body

    on_click_body = extract_method_body(front_source, "def _on_click", "class RecordsWidget")

    assert "pomodoro_preserve_on_record_change" in on_click_body
    assert "and not window.simplesettings.get" in on_click_body


def extract_method_body(source, method_start, next_method):
    """Extract the body of a method from source code.
    
    This is a simple heuristic that finds the method start and returns
    everything until the next method or class starts.
    """
    lines = source.split("\n")
    in_method = False
    method_lines = []
    indent_level = 0

    for i, line in enumerate(lines):
        if method_start in line:
            in_method = True
            indent_level = len(line) - len(line.lstrip())
            method_lines.append(line)
            continue
        
        if in_method:
            current_indent = len(line) - len(line.lstrip())
            
            if line.strip() and not line.strip().startswith("#") and current_indent <= indent_level and current_indent > 0:
                method_lines.append(line)
            elif line.strip().startswith("def ") or line.strip().startswith("class "):
                break
            else:
                method_lines.append(line)

    return "\n".join(method_lines)


def extract_section(source, section_start, section_end):
    """Extract a section of code between two markers."""
    if section_start not in source:
        return ""
    
    start_idx = source.find(section_start)
    if section_end and section_end in source[start_idx:]:
        end_idx = source.find(section_end, start_idx)
        return source[start_idx:end_idx]
    return source[start_idx:]


if __name__ == "__main__":
    run_tests(globals())
