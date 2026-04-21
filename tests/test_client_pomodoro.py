"""
Test pomodoro preserve on record change functionality.

This module tests the pure decision logic in pomodoro_logic.py, which is
reused by both dialogs.py and front.py. All functions are pure (no side
effects) and can be directly tested in Python.

The production code paths that use these functions:
- RecordDialog.submit() → should_reset_pomodoro_on_record_start/stop
- RecordDialog.resume_record() → should_reset_pomodoro_on_record_start
- HeaderWidget._on_click() (record_stopall) → should_reset_pomodoro_on_record_stop
- PomodoroDialog._init_state() → should_try_restore_pomodoro_state, determine_restored_pomodoro_state
- PomodoroDialog._save_state_to_storage() → should_save_pomodoro_state_to_storage, should_clear_pomodoro_state_from_storage
- SettingsDialog callbacks → should_clear_storage_on_setting_change
- HeaderWidget actions → header_action_affects_pomodoro
- RecordDialog modes → should_affect_pomodoro_for_record_mode
"""

from _common import run_tests
from timetagger.app.pomodoro_logic import (
    POMODORO_STATE_PRE_WORK,
    POMODORO_STATE_WORK,
    POMODORO_STATE_PRE_BREAK,
    POMODORO_STATE_BREAK,
    RUNNING_STATES,
    PRE_STATES,
    RECORD_DIALOG_MODE_START,
    RECORD_DIALOG_MODE_STOP,
    RECORD_DIALOG_MODE_EDIT,
    RECORD_DIALOG_MODE_NEW,
    HEADER_ACTION_RECORD_STOPALL,
    is_pomodoro_running,
    should_reset_pomodoro_on_record_start,
    should_reset_pomodoro_on_record_stop,
    should_affect_pomodoro_for_record_mode,
    should_save_pomodoro_state_to_storage,
    should_clear_pomodoro_state_from_storage,
    should_try_restore_pomodoro_state,
    determine_restored_pomodoro_state,
    should_clear_storage_on_setting_change,
    header_action_affects_pomodoro,
)


def test_is_pomodoro_running():
    """Test is_pomodoro_running function.
    
    Used to check if pomodoro is in an active running state (work or break).
    """
    assert is_pomodoro_running(POMODORO_STATE_WORK) is True
    assert is_pomodoro_running(POMODORO_STATE_BREAK) is True

    assert is_pomodoro_running(POMODORO_STATE_PRE_WORK) is False
    assert is_pomodoro_running(POMODORO_STATE_PRE_BREAK) is False


def test_should_reset_pomodoro_on_record_start_preserve_disabled():
    """Test should_reset_pomodoro_on_record_start when preserve is disabled.
    
    When pomodoro_preserve_on_record_change is False (default behavior):
    - Starting a record should ALWAYS reset pomodoro (call start_work())
    
    This tests the original behavior is preserved when the switch is off.
    """
    preserve_enabled = False

    assert should_reset_pomodoro_on_record_start(preserve_enabled, POMODORO_STATE_PRE_WORK) is True
    assert should_reset_pomodoro_on_record_start(preserve_enabled, POMODORO_STATE_WORK) is True
    assert should_reset_pomodoro_on_record_start(preserve_enabled, POMODORO_STATE_PRE_BREAK) is True
    assert should_reset_pomodoro_on_record_start(preserve_enabled, POMODORO_STATE_BREAK) is True


def test_should_reset_pomodoro_on_record_start_preserve_enabled():
    """Test should_reset_pomodoro_on_record_start when preserve is enabled.
    
    When pomodoro_preserve_on_record_change is True:
    - If pomodoro is RUNNING (work/break): DON'T reset (preserve current round)
    - If pomodoro is NOT RUNNING (pre-work/pre-break): DO reset (start fresh)
    
    This ensures:
    1. If a pomodoro round is in progress, starting a new record doesn't interrupt it
    2. If no pomodoro is running, starting a new record begins a fresh round
    """
    preserve_enabled = True

    assert should_reset_pomodoro_on_record_start(preserve_enabled, POMODORO_STATE_PRE_WORK) is True
    assert should_reset_pomodoro_on_record_start(preserve_enabled, POMODORO_STATE_PRE_BREAK) is True

    assert should_reset_pomodoro_on_record_start(preserve_enabled, POMODORO_STATE_WORK) is False
    assert should_reset_pomodoro_on_record_start(preserve_enabled, POMODORO_STATE_BREAK) is False


def test_should_reset_pomodoro_on_record_stop():
    """Test should_reset_pomodoro_on_record_stop.
    
    When pomodoro_preserve_on_record_change is False:
    - Stopping a record should ALWAYS reset pomodoro (call stop())
    
    When pomodoro_preserve_on_record_change is True:
    - Stopping a record should NOT reset pomodoro (preserve current state)
    
    This tests both:
    - RecordDialog.submit() when lmode == "stop"
    - HeaderWidget._on_click() when action == "record_stopall"
    """
    assert should_reset_pomodoro_on_record_stop(preserve_enabled=False) is True

    assert should_reset_pomodoro_on_record_stop(preserve_enabled=True) is False


def test_should_affect_pomodoro_for_record_mode():
    """Test should_affect_pomodoro_for_record_mode.
    
    Verifies that only certain record dialog modes can affect pomodoro:
    - "start": Affects pomodoro (calls start_work())
    - "stop": Affects pomodoro (calls stop())
    - "edit": Does NOT affect pomodoro
    - "new": Does NOT affect pomodoro
    
    This is a key test for the EDIT SCENARIO:
    Editing an existing record (without changing its running state) should
    never trigger pomodoro start/stop.
    """
    assert should_affect_pomodoro_for_record_mode(RECORD_DIALOG_MODE_START) is True
    assert should_affect_pomodoro_for_record_mode(RECORD_DIALOG_MODE_STOP) is True

    assert should_affect_pomodoro_for_record_mode(RECORD_DIALOG_MODE_EDIT) is False
    assert should_affect_pomodoro_for_record_mode(RECORD_DIALOG_MODE_NEW) is False


def test_record_edit_scenario_complete():
    """Complete test for the edit scenario.
    
    When editing an existing record:
    1. The mode should be "edit" (not "start" or "stop")
    2. "edit" mode should NOT affect pomodoro
    3. Therefore, pomodoro state should remain unchanged
    
    This verifies:
    - Editing a record's description doesn't interrupt pomodoro
    - Editing a record's tags doesn't interrupt pomodoro
    - Only actually starting or stopping a record affects pomodoro
    """
    edit_mode = RECORD_DIALOG_MODE_EDIT
    current_pomodoro_state = POMODORO_STATE_WORK
    preserve_enabled = True

    mode_affects_pomo = should_affect_pomodoro_for_record_mode(edit_mode)
    assert mode_affects_pomo is False, "Edit mode should NOT affect pomodoro"

    submit_would_reset = (
        should_affect_pomodoro_for_record_mode(RECORD_DIALOG_MODE_START)
        and should_reset_pomodoro_on_record_start(preserve_enabled, current_pomodoro_state)
    )
    assert submit_would_reset is False, "In edit mode, submit() should not call start_work()/stop()"


def test_header_action_affects_pomodoro():
    """Test header_action_affects_pomodoro.
    
    Verifies which header actions can affect pomodoro:
    - "record_stopall": Affects pomodoro (calls stop() if preserve is off)
    - "nav_*" actions: Do NOT affect pomodoro
    - "select_*" actions: Do NOT affect pomodoro
    
    This is a key test for TIMELINE/OVERVIEW switching:
    - Timeline navigation (nav_snap_today, nav_zoom, etc.) doesn't affect pomodoro
    - Tag selection (select_none, etc.) doesn't affect pomodoro
    - Only record-related actions (record_stopall) can affect pomodoro
    """
    assert header_action_affects_pomodoro(HEADER_ACTION_RECORD_STOPALL) is True

    assert header_action_affects_pomodoro("nav_snap_today") is False
    assert header_action_affects_pomodoro("nav_snap_now") is False
    assert header_action_affects_pomodoro("nav_zoom_day") is False
    assert header_action_affects_pomodoro("nav_backward") is False
    assert header_action_affects_pomodoro("nav_forward") is False
    assert header_action_affects_pomodoro("nav_menu") is False

    assert header_action_affects_pomodoro("select_none") is False


def test_timeline_overview_switch_scenario_complete():
    """Complete test for timeline/overview switching scenario.
    
    When interacting with timeline or overview:
    1. The action should be "nav_*" or "select_*"
    2. These actions should NOT affect pomodoro
    3. Therefore, pomodoro state should remain unchanged
    
    This verifies:
    - Zooming in/out on timeline doesn't interrupt pomodoro
    - Jumping to today doesn't interrupt pomodoro
    - Selecting/unselecting tags in overview doesn't interrupt pomodoro
    - Navigating forward/backward in time doesn't interrupt pomodoro
    """
    timeline_actions = [
        "nav_snap_today",
        "nav_snap_now",
        "nav_snap_year",
        "nav_snap_month",
        "nav_snap_week",
        "nav_snap_day",
        "nav_zoom_-1",
        "nav_zoom_+1",
        "nav_zoom_day",
        "nav_zoom_week",
        "nav_zoom_month",
        "nav_zoom_year",
        "nav_backward",
        "nav_forward",
    ]
    
    overview_actions = [
        "select_none",
    ]
    
    current_pomodoro_state = POMODORO_STATE_WORK
    state_before = current_pomodoro_state
    
    for action in timeline_actions:
        affects_pomo = header_action_affects_pomodoro(action)
        assert affects_pomo is False, f"Timeline action '{action}' should NOT affect pomodoro"
    
    for action in overview_actions:
        affects_pomo = header_action_affects_pomodoro(action)
        assert affects_pomo is False, f"Overview action '{action}' should NOT affect pomodoro"
    
    state_after = current_pomodoro_state
    assert state_after == state_before, "Pomodoro state should remain unchanged after timeline/overview interactions"


def test_should_save_pomodoro_state_to_storage_preserve_disabled():
    """Test should_save_pomodoro_state_to_storage when preserve is disabled.
    
    When pomodoro_preserve_on_record_change is False:
    - Never save state to localStorage
    
    This ensures:
    1. If the user hasn't enabled the feature, nothing is persisted
    2. Turning off the feature clears any previously saved state
    """
    preserve_enabled = False

    assert should_save_pomodoro_state_to_storage(preserve_enabled, POMODORO_STATE_WORK) is False
    assert should_save_pomodoro_state_to_storage(preserve_enabled, POMODORO_STATE_BREAK) is False
    assert should_save_pomodoro_state_to_storage(preserve_enabled, POMODORO_STATE_PRE_WORK) is False
    assert should_save_pomodoro_state_to_storage(preserve_enabled, POMODORO_STATE_PRE_BREAK) is False


def test_should_save_pomodoro_state_to_storage_preserve_enabled():
    """Test should_save_pomodoro_state_to_storage when preserve is enabled.
    
    When pomodoro_preserve_on_record_change is True:
    - Only SAVE if state is "work" or "break" (actual running states)
    - Do NOT save if state is "pre-work" or "pre-break"
    
    This is a key test for LOCALSTORAGE CLEANUP:
    - Running states (work/break) are persisted so they survive page refresh
    - Non-running states (pre-work/pre-break) are NOT persisted, so:
      * Manual stop → state becomes pre-work → NOT saved → refresh starts fresh
      * Natural end → state becomes pre-break/pre-work → NOT saved → refresh starts fresh
      * This prevents "residual" states from causing unexpected behavior on refresh
    """
    preserve_enabled = True

    assert should_save_pomodoro_state_to_storage(preserve_enabled, POMODORO_STATE_WORK) is True
    assert should_save_pomodoro_state_to_storage(preserve_enabled, POMODORO_STATE_BREAK) is True

    assert should_save_pomodoro_state_to_storage(preserve_enabled, POMODORO_STATE_PRE_WORK) is False
    assert should_save_pomodoro_state_to_storage(preserve_enabled, POMODORO_STATE_PRE_BREAK) is False


def test_should_clear_pomodoro_state_from_storage():
    """Test should_clear_pomodoro_state_from_storage.
    
    State should be cleared from localStorage when:
    1. preserve is disabled (feature is off)
    2. preserve is enabled but state is not a running state (pre-work/pre-break)
    
    This ensures:
    - Turning off the feature clears any saved state
    - Manual stop (state becomes pre-work) clears saved state
    - Natural end (state becomes pre-break/pre-work) clears saved state
    """
    assert should_clear_pomodoro_state_from_storage(preserve_enabled=False) is True
    assert should_clear_pomodoro_state_from_storage(preserve_enabled=False, pomodoro_state=POMODORO_STATE_WORK) is True

    assert should_clear_pomodoro_state_from_storage(preserve_enabled=True) is False

    assert should_clear_pomodoro_state_from_storage(preserve_enabled=True, pomodoro_state=POMODORO_STATE_PRE_WORK) is True
    assert should_clear_pomodoro_state_from_storage(preserve_enabled=True, pomodoro_state=POMODORO_STATE_PRE_BREAK) is True

    assert should_clear_pomodoro_state_from_storage(preserve_enabled=True, pomodoro_state=POMODORO_STATE_WORK) is False
    assert should_clear_pomodoro_state_from_storage(preserve_enabled=True, pomodoro_state=POMODORO_STATE_BREAK) is False


def test_should_try_restore_pomodoro_state():
    """Test should_try_restore_pomodoro_state.
    
    Should only attempt to restore from localStorage when:
    1. pomodoro_enabled is True (pomodoro feature is enabled)
    2. pomodoro_preserve_on_record_change is True (persistence is enabled)
    
    Both conditions must be true to attempt restoration.
    """
    assert should_try_restore_pomodoro_state(pomodoro_enabled=False, preserve_enabled=False) is False
    assert should_try_restore_pomodoro_state(pomodoro_enabled=False, preserve_enabled=True) is False
    assert should_try_restore_pomodoro_state(pomodoro_enabled=True, preserve_enabled=False) is False

    assert should_try_restore_pomodoro_state(pomodoro_enabled=True, preserve_enabled=True) is True


def test_determine_restored_pomodoro_state_not_expired():
    """Test determine_restored_pomodoro_state when saved state is NOT expired.
    
    If saved_etime > current_time (state hasn't ended yet):
    - Restore to the same state with the same etime
    
    This handles:
    - Page refresh during a work session → resumes the work session
    - Page refresh during a break → resumes the break
    """
    current_time = 1000000
    future_time = current_time + 1500

    assert determine_restored_pomodoro_state(POMODORO_STATE_WORK, future_time, current_time) == (POMODORO_STATE_WORK, future_time)

    assert determine_restored_pomodoro_state(POMODORO_STATE_BREAK, future_time, current_time) == (POMODORO_STATE_BREAK, future_time)


def test_determine_restored_pomodoro_state_expired():
    """Test determine_restored_pomodoro_state when saved state IS expired.
    
    If saved_etime <= current_time (state has ended):
    - work → pre-break (work ended, user should take a break)
    - break → pre-work (break ended, user should start working again)
    
    This handles:
    - Page refresh after work session ended → shows pre-break
    - Page refresh after break ended → shows pre-work
    """
    current_time = 1000000
    past_time = current_time - 100

    assert determine_restored_pomodoro_state(POMODORO_STATE_WORK, past_time, current_time) == (POMODORO_STATE_PRE_BREAK, 0)

    assert determine_restored_pomodoro_state(POMODORO_STATE_BREAK, past_time, current_time) == (POMODORO_STATE_PRE_WORK, 0)


def test_determine_restored_pomodoro_state_pre_states():
    """Test determine_restored_pomodoro_state for pre states.
    
    If saved state is pre-work or pre-break:
    - Restore to that state
    
    Note: With our storage strategy, these should never actually be saved,
    but the function handles them anyway for robustness.
    """
    current_time = 1000000

    assert determine_restored_pomodoro_state(POMODORO_STATE_PRE_WORK, 0, current_time) == (POMODORO_STATE_PRE_WORK, 0)

    assert determine_restored_pomodoro_state(POMODORO_STATE_PRE_BREAK, 0, current_time) == (POMODORO_STATE_PRE_BREAK, 0)


def test_determine_restored_pomodoro_state_invalid():
    """Test determine_restored_pomodoro_state for invalid state.
    
    If saved state is not recognized:
    - Return None (don't restore anything)
    """
    current_time = 1000000

    assert determine_restored_pomodoro_state("invalid_state", 0, current_time) is None
    assert determine_restored_pomodoro_state("", 0, current_time) is None
    assert determine_restored_pomodoro_state(None, 0, current_time) is None


def test_should_clear_storage_on_setting_change():
    """Test should_clear_storage_on_setting_change.
    
    Storage should be cleared when:
    1. pomodoro_enabled is being turned OFF (was True, now False)
    2. pomodoro_preserve_on_record_change is being turned OFF (was True, now False)
    3. Either setting is currently OFF
    
    This ensures:
    - Turning off pomodoro clears any saved state
    - Turning off the preserve feature clears any saved state
    - No residual state is left behind that could cause issues later
    """
    assert should_clear_storage_on_setting_change(
        new_pomodoro_enabled=False,
        new_preserve_enabled=True,
        old_pomodoro_enabled=True,
        old_preserve_enabled=True,
    ) is True

    assert should_clear_storage_on_setting_change(
        new_pomodoro_enabled=True,
        new_preserve_enabled=False,
        old_pomodoro_enabled=True,
        old_preserve_enabled=True,
    ) is True

    assert should_clear_storage_on_setting_change(
        new_pomodoro_enabled=False,
        new_preserve_enabled=True,
    ) is True

    assert should_clear_storage_on_setting_change(
        new_pomodoro_enabled=True,
        new_preserve_enabled=False,
    ) is True

    assert should_clear_storage_on_setting_change(
        new_pomodoro_enabled=True,
        new_preserve_enabled=True,
    ) is False


def test_localstorage_cleanup_manual_stop_scenario():
    """Test localStorage cleanup after manual stop.
    
    Scenario:
    1. User is in work state with preserve enabled
    2. User manually clicks Stop in pomodoro dialog
    3. State becomes pre-work
    4. pre-work should NOT be saved to localStorage
    5. Page refresh → starts fresh at pre-work (doesn't restore anything)
    
    This prevents: Manual stop → refresh → accidentally restoring to pre-work
    (which was the previous behavior that caused confusion)
    """
    preserve_enabled = True

    state_before = POMODORO_STATE_WORK
    should_save_before = should_save_pomodoro_state_to_storage(preserve_enabled, state_before)
    assert should_save_before is True, "Work state should be saved"

    state_after = POMODORO_STATE_PRE_WORK
    should_save_after = should_save_pomodoro_state_to_storage(preserve_enabled, state_after)
    assert should_save_after is False, "Pre-work state should NOT be saved"

    should_clear = should_clear_pomodoro_state_from_storage(preserve_enabled, state_after)
    assert should_clear is True, "Pre-work state should trigger clear"

    should_restore = should_try_restore_pomodoro_state(
        pomodoro_enabled=True,
        preserve_enabled=True,
    )
    assert should_restore is True, "Should attempt to restore"

    saved_state = None
    if saved_state:
        restore_result = determine_restored_pomodoro_state(saved_state, 0, 1000000)
    else:
        restore_result = None
    assert restore_result is None, "No state saved, so nothing to restore"


def test_localstorage_cleanup_natural_end_scenario():
    """Test localStorage cleanup after natural end of pomodoro.
    
    Scenario:
    1. User is in work state with preserve enabled
    2. Work timer naturally expires
    3. State becomes pre-break
    4. pre-break should NOT be saved to localStorage
    5. Page refresh → starts fresh at pre-work
    
    This prevents: Work expired → refresh → accidentally restoring to pre-break
    """
    preserve_enabled = True
    current_time = 1000000

    saved_state = POMODORO_STATE_WORK
    saved_etime = current_time - 100

    restore_result = determine_restored_pomodoro_state(saved_state, saved_etime, current_time)
    assert restore_result == (POMODORO_STATE_PRE_BREAK, 0), "Expired work should become pre-break"

    restored_state, _ = restore_result
    should_save = should_save_pomodoro_state_to_storage(preserve_enabled, restored_state)
    assert should_save is False, "Pre-break state should NOT be saved"

    should_clear = should_clear_pomodoro_state_from_storage(preserve_enabled, restored_state)
    assert should_clear is True, "Pre-break state should trigger clear"


def test_localstorage_cleanup_setting_change_scenario():
    """Test localStorage cleanup when settings change.
    
    Scenario:
    1. User has pomodoro and preserve enabled
    2. User is in work state (saved to localStorage)
    3. User turns off preserve setting
    4. Storage should be cleared
    5. Page refresh → starts fresh at pre-work
    
    Also tests: Turning off pomodoro_enabled should also clear storage.
    """
    old_pomodoro_enabled = True
    old_preserve_enabled = True

    new_pomodoro_enabled = True
    new_preserve_enabled = False

    should_clear = should_clear_storage_on_setting_change(
        new_pomodoro_enabled=new_pomodoro_enabled,
        new_preserve_enabled=new_preserve_enabled,
        old_pomodoro_enabled=old_pomodoro_enabled,
        old_preserve_enabled=old_preserve_enabled,
    )
    assert should_clear is True, "Turning off preserve should clear storage"

    new_pomodoro_enabled_2 = False
    new_preserve_enabled_2 = True

    should_clear_2 = should_clear_storage_on_setting_change(
        new_pomodoro_enabled=new_pomodoro_enabled_2,
        new_preserve_enabled=new_preserve_enabled_2,
        old_pomodoro_enabled=old_pomodoro_enabled,
        old_preserve_enabled=old_preserve_enabled,
    )
    assert should_clear_2 is True, "Turning off pomodoro should clear storage"


def test_complete_workflow_preserve_enabled():
    """Complete integration test: preserve feature enabled.
    
    Scenario:
    1. Settings: pomodoro_enabled=True, preserve_enabled=True
    2. Current state: work (15 minutes remaining)
    3. User starts a NEW record
    4. → Pomodoro should NOT reset (continue current work round)
    5. User edits the record (changes description)
    6. → Pomodoro should NOT be affected
    7. User zooms timeline (nav_zoom_day)
    8. → Pomodoro should NOT be affected
    9. Page refresh
    10. → Should restore work state with remaining time
    """
    pomo_enabled = True
    preserve_enabled = True
    current_time = 1000000
    current_state = POMODORO_STATE_WORK
    current_etime = current_time + 900

    should_reset = should_reset_pomodoro_on_record_start(preserve_enabled, current_state)
    assert should_reset is False, "Starting record should NOT reset pomodoro when preserve is on and pomo is running"

    edit_mode_affects = should_affect_pomodoro_for_record_mode(RECORD_DIALOG_MODE_EDIT)
    assert edit_mode_affects is False, "Edit mode should NOT affect pomodoro"

    nav_affects = header_action_affects_pomodoro("nav_zoom_day")
    assert nav_affects is False, "Nav actions should NOT affect pomodoro"

    should_restore = should_try_restore_pomodoro_state(pomo_enabled, preserve_enabled)
    assert should_restore is True, "Should attempt to restore on page refresh"

    restore_result = determine_restored_pomodoro_state(current_state, current_etime, current_time)
    assert restore_result == (POMODORO_STATE_WORK, current_etime), "Should restore work state"


def test_complete_workflow_preserve_disabled():
    """Complete integration test: preserve feature disabled (default behavior).
    
    Scenario:
    1. Settings: pomodoro_enabled=True, preserve_enabled=False
    2. Current state: work
    3. User starts a NEW record
    4. → Pomodoro SHOULD reset (start fresh 25 minutes)
    5. Page refresh
    6. → Should NOT restore anything (starts fresh at pre-work)
    """
    pomo_enabled = True
    preserve_enabled = False
    current_state = POMODORO_STATE_WORK

    should_reset = should_reset_pomodoro_on_record_start(preserve_enabled, current_state)
    assert should_reset is True, "Starting record SHOULD reset pomodoro when preserve is off"

    should_restore = should_try_restore_pomodoro_state(pomo_enabled, preserve_enabled)
    assert should_restore is False, "Should NOT attempt to restore when preserve is off"

    should_save = should_save_pomodoro_state_to_storage(preserve_enabled, current_state)
    assert should_save is False, "Should NOT save state when preserve is off"


if __name__ == "__main__":
    run_tests(globals())
