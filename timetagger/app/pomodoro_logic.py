"""
Pomodoro logic module - shared decision logic for pomodoro functionality.

This module contains the pure decision logic that can be tested in isolation
without requiring a browser environment. The actual dialog and front code
reuse these functions to make decisions.

All functions are pure (no side effects) and can be directly tested.
"""

POMODORO_STATE_PRE_WORK = "pre-work"
POMODORO_STATE_WORK = "work"
POMODORO_STATE_PRE_BREAK = "pre-break"
POMODORO_STATE_BREAK = "break"

RUNNING_STATES = (POMODORO_STATE_WORK, POMODORO_STATE_BREAK)
PRE_STATES = (POMODORO_STATE_PRE_WORK, POMODORO_STATE_PRE_BREAK)

RECORD_DIALOG_MODE_START = "start"
RECORD_DIALOG_MODE_STOP = "stop"
RECORD_DIALOG_MODE_EDIT = "edit"
RECORD_DIALOG_MODE_NEW = "new"

HEADER_ACTION_RECORD_STOPALL = "record_stopall"


def is_pomodoro_running(current_state):
    """
    Check if pomodoro is currently running (in work or break state).
    
    Args:
        current_state: str, current pomodoro state
        
    Returns:
        bool: True if state is work or break
    """
    return current_state in RUNNING_STATES


def should_reset_pomodoro_on_record_start(preserve_enabled, current_pomodoro_state):
    """
    Determine whether to reset pomodoro when starting a new record.
    
    This is used in:
    - RecordDialog.submit() when lmode == "start"
    - RecordDialog.resume_record()
    
    Logic:
    - If preserve is disabled: always reset (existing behavior)
    - If preserve is enabled:
      - If pomodoro is running (work/break): don't reset
      - If pomodoro is NOT running (pre-work/pre-break): reset (start fresh)
    
    Args:
        preserve_enabled: bool, pomodoro_preserve_on_record_change setting
        current_pomodoro_state: str, current pomodoro state
        
    Returns:
        bool: True if pomodoro should be reset (call start_work())
    """
    if not preserve_enabled:
        return True
    
    is_running = is_pomodoro_running(current_pomodoro_state)
    if not is_running:
        return True
    
    return False


def should_reset_pomodoro_on_record_stop(preserve_enabled):
    """
    Determine whether to reset pomodoro when stopping a record.
    
    This is used in:
    - RecordDialog.submit() when lmode == "stop"
    - HeaderWidget._on_click() when action == "record_stopall"
    
    Logic:
    - If preserve is disabled: reset (existing behavior)
    - If preserve is enabled: don't reset
    
    Args:
        preserve_enabled: bool, pomodoro_preserve_on_record_change setting
        
    Returns:
        bool: True if pomodoro should be reset (call stop())
    """
    return not preserve_enabled


def should_affect_pomodoro_for_record_mode(record_mode):
    """
    Determine whether the given record dialog mode can affect pomodoro state.
    
    This is used to verify that edit/new modes don't affect pomodoro.
    
    Logic:
    - Only "start" and "stop" modes can affect pomodoro
    - "edit" and "new" modes should never affect pomodoro
    
    Args:
        record_mode: str, the lmode value ("start", "stop", "edit", "new")
        
    Returns:
        bool: True if this mode can trigger pomodoro start/stop
    """
    return record_mode in (RECORD_DIALOG_MODE_START, RECORD_DIALOG_MODE_STOP)


def should_save_pomodoro_state_to_storage(preserve_enabled, pomodoro_state):
    """
    Determine whether to save pomodoro state to localStorage.
    
    This is used in PomodoroDialog._save_state_to_storage().
    
    Logic:
    - If preserve is disabled: don't save (clear instead)
    - If preserve is enabled:
      - Only save if state is "work" or "break" (actual running states)
      - Don't save if state is "pre-work" or "pre-break" (clear instead)
    
    Args:
        preserve_enabled: bool, pomodoro_preserve_on_record_change setting
        pomodoro_state: str, current pomodoro state
        
    Returns:
        bool: True if state should be saved to localStorage
    """
    if not preserve_enabled:
        return False
    
    return pomodoro_state in RUNNING_STATES


def should_clear_pomodoro_state_from_storage(preserve_enabled, pomodoro_state=None):
    """
    Determine whether to clear pomodoro state from localStorage.
    
    This is the inverse of should_save_pomodoro_state_to_storage().
    
    Logic:
    - Clear when:
      1. Preserve is disabled
      2. Preserve is enabled but state is not a running state
      
    Args:
        preserve_enabled: bool, pomodoro_preserve_on_record_change setting
        pomodoro_state: str, optional, current pomodoro state
        
    Returns:
        bool: True if stored state should be cleared
    """
    if not preserve_enabled:
        return True
    
    if pomodoro_state is None:
        return False
    
    return pomodoro_state in PRE_STATES


def should_try_restore_pomodoro_state(pomodoro_enabled, preserve_enabled):
    """
    Determine whether to try restoring pomodoro state from localStorage on init.
    
    This is used in PomodoroDialog._init_state().
    
    Logic:
    - Only try to restore if both pomodoro_enabled AND pomodoro_preserve_on_record_change are True
    
    Args:
        pomodoro_enabled: bool, pomodoro_enabled setting
        preserve_enabled: bool, pomodoro_preserve_on_record_change setting
        
    Returns:
        bool: True if should attempt to restore state from storage
    """
    return pomodoro_enabled and preserve_enabled


def determine_restored_pomodoro_state(saved_state, saved_etime, current_time):
    """
    Determine what state to restore from localStorage.
    
    This is used in PomodoroDialog._init_state() when restoring.
    
    Logic:
    - If saved_state is "work" or "break":
      - If saved_etime > current_time (state not expired): restore with saved_etime
      - If saved_etime <= current_time (state expired):
        - work -> pre-break
        - break -> pre-work
    - If saved_state is "pre-work" or "pre-break":
      - Note: These should never be saved per should_save_pomodoro_state_to_storage()
      - But if they are somehow present, restore them
    - Otherwise: return None (invalid state)
    
    Args:
        saved_state: str, state from localStorage
        saved_etime: float, end time from localStorage
        current_time: float, current timestamp
        
    Returns:
        tuple: (state_to_set, etime_to_use) or None if state is invalid
    """
    if saved_state in RUNNING_STATES:
        if saved_etime > current_time:
            return (saved_state, saved_etime)
        else:
            if saved_state == POMODORO_STATE_WORK:
                return (POMODORO_STATE_PRE_BREAK, 0)
            else:
                return (POMODORO_STATE_PRE_WORK, 0)
    elif saved_state in PRE_STATES:
        return (saved_state, 0)
    return None


def should_clear_storage_on_setting_change(new_pomodoro_enabled, new_preserve_enabled, 
                                            old_pomodoro_enabled=None, old_preserve_enabled=None):
    """
    Determine whether to clear storage when settings change.
    
    This is used in:
    - SettingsDialog._on_pomodoro_check()
    - SettingsDialog._on_pomodoro_preserve_check()
    
    Logic:
    - Clear when:
      1. pomodoro_enabled is being turned OFF (was True, now False)
      2. pomodoro_preserve_on_record_change is being turned OFF (was True, now False)
      
    Args:
        new_pomodoro_enabled: bool, new value of pomodoro_enabled
        new_preserve_enabled: bool, new value of pomodoro_preserve_on_record_change
        old_pomodoro_enabled: bool, optional, old value of pomodoro_enabled
        old_preserve_enabled: bool, optional, old value of pomodoro_preserve_on_record_change
        
    Returns:
        bool: True if stored state should be cleared
    """
    if old_pomodoro_enabled is not None and old_pomodoro_enabled and not new_pomodoro_enabled:
        return True
    
    if old_preserve_enabled is not None and old_preserve_enabled and not new_preserve_enabled:
        return True
    
    if not new_pomodoro_enabled:
        return True
    
    if not new_preserve_enabled:
        return True
    
    return False


def header_action_affects_pomodoro(action):
    """
    Determine whether a header action can affect pomodoro state.
    
    This is used to verify that nav_* and select_* actions don't affect pomodoro.
    
    Logic:
    - Only "record_stopall" can affect pomodoro
    - "nav_*" and "select_*" actions should never affect pomodoro
    
    Args:
        action: str, the action string
        
    Returns:
        bool: True if this action can affect pomodoro state
    """
    if action == HEADER_ACTION_RECORD_STOPALL:
        return True
    
    if action.startswith("nav_") or action.startswith("select_"):
        return False
    
    return False
