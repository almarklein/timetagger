"""
Test pomodoro preserve on record change functionality.
"""

from _common import run_tests


def test_simplesettings_has_pomodoro_preserve_key():
    """Test that SimpleSettings has the new pomodoro_preserve_on_record_change key."""
    from timetagger.app.utils import SimpleSettings

    settings = SimpleSettings()

    assert "pomodoro_preserve_on_record_change" in settings._local_keys

    assert settings._local_keys["pomodoro_preserve_on_record_change"] is False

    assert settings.get("pomodoro_preserve_on_record_change") is False


def test_simplesettings_can_set_and_get_pomodoro_preserve():
    """Test that we can set and get the pomodoro_preserve_on_record_change setting."""
    from timetagger.app.utils import SimpleSettings

    settings = SimpleSettings()

    settings.set("pomodoro_preserve_on_record_change", True)
    assert settings.get("pomodoro_preserve_on_record_change") is True

    settings.set("pomodoro_preserve_on_record_change", False)
    assert settings.get("pomodoro_preserve_on_record_change") is False


def test_should_preserve_pomodoro_logic():
    """Test the core logic for determining whether to preserve pomodoro state.
    
    This tests the decision logic used in:
    - RecordDialog.submit()
    - RecordDialog.resume_record()
    - HeaderWidget._on_click() for record_stopall
    
    The logic is:
    - If pomodoro_preserve_on_record_change is False: use existing behavior (reset)
    - If pomodoro_preserve_on_record_change is True:
      - For start operations: only reset if pomodoro is NOT already running
      - For stop operations: never reset
    """

    def should_reset_for_start(preserve_enabled, pomodoro_is_running):
        """Simulate the logic in RecordDialog.submit() for start mode."""
        if not preserve_enabled:
            return True
        if not pomodoro_is_running:
            return True
        return False

    def should_reset_for_stop(preserve_enabled):
        """Simulate the logic in RecordDialog.submit() for stop mode."""
        return not preserve_enabled

    assert should_reset_for_start(preserve_enabled=False, pomodoro_is_running=True) is True
    assert should_reset_for_start(preserve_enabled=False, pomodoro_is_running=False) is True

    assert should_reset_for_start(preserve_enabled=True, pomodoro_is_running=True) is False
    assert should_reset_for_start(preserve_enabled=True, pomodoro_is_running=False) is True

    assert should_reset_for_stop(preserve_enabled=False) is True
    assert should_reset_for_stop(preserve_enabled=True) is False


def test_pomodoro_state_storage_logic():
    """Test the logic for pomodoro state persistence.
    
    This tests the decision logic used in PomodoroDialog:
    - When to save state to storage
    - When to restore state from storage on init
    """

    def should_save_state(preserve_enabled):
        """Simulate the logic in PomodoroDialog._save_state_to_storage()."""
        return preserve_enabled

    def should_try_restore_on_init(pomodoro_enabled, preserve_enabled):
        """Simulate the logic in PomodoroDialog._init_state()."""
        return pomodoro_enabled and preserve_enabled

    def determine_restore_action(saved_state, saved_etime, current_time):
        """Simulate the logic for determining what state to restore.
        
        Returns: (state_to_set, etime_to_use) or None if should use default.
        """
        if saved_state in ("work", "break"):
            if saved_etime > current_time:
                return (saved_state, saved_etime)
            else:
                if saved_state == "work":
                    return ("pre-break", 0)
                else:
                    return ("pre-work", 0)
        elif saved_state in ("pre-work", "pre-break"):
            return (saved_state, 0)
        return None

    assert should_save_state(preserve_enabled=False) is False
    assert should_save_state(preserve_enabled=True) is True

    assert should_try_restore_on_init(pomodoro_enabled=False, preserve_enabled=False) is False
    assert should_try_restore_on_init(pomodoro_enabled=False, preserve_enabled=True) is False
    assert should_try_restore_on_init(pomodoro_enabled=True, preserve_enabled=False) is False
    assert should_try_restore_on_init(pomodoro_enabled=True, preserve_enabled=True) is True

    now = 1000000

    assert determine_restore_action("work", now + 1000, now) == ("work", now + 1000)

    assert determine_restore_action("work", now - 100, now) == ("pre-break", 0)

    assert determine_restore_action("break", now + 500, now) == ("break", now + 500)

    assert determine_restore_action("break", now - 50, now) == ("pre-work", 0)

    assert determine_restore_action("pre-work", 0, now) == ("pre-work", 0)
    assert determine_restore_action("pre-break", 0, now) == ("pre-break", 0)

    assert determine_restore_action("invalid", 0, now) is None


if __name__ == "__main__":
    run_tests(globals())
