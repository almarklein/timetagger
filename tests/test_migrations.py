import importlib
import logging
from _common import run_tests


def test_migration_001_happy_path(tmp_path, monkeypatch):
    """Test standard migration where old exists and new does not."""
    mig = importlib.import_module("timetagger.migrations.001_datadir_default_xdg")

    old_dir = tmp_path / "old" / "_timetagger"
    new_dir = tmp_path / "new" / "timetagger"

    monkeypatch.setattr(mig, "get_old_default_dir", lambda: old_dir)
    monkeypatch.setattr(mig, "get_new_default_dir", lambda: new_dir)

    old_dir.mkdir(parents=True)
    (old_dir / "jwt.key").write_text("fake key")

    mig.run(str(new_dir))

    assert not old_dir.exists()
    assert new_dir.exists()
    assert (new_dir / "jwt.key").read_text() == "fake key"


def test_migration_001_custom_path_skipped(tmp_path, monkeypatch):
    """Test that custom config dirs cause the migration to safely abort."""
    mig = importlib.import_module("timetagger.migrations.001_datadir_default_xdg")

    old_dir = tmp_path / "old" / "_timetagger"
    new_dir = tmp_path / "new" / "timetagger"
    custom_dir = tmp_path / "custom" / "timetagger"

    monkeypatch.setattr(mig, "get_old_default_dir", lambda: old_dir)
    monkeypatch.setattr(mig, "get_new_default_dir", lambda: new_dir)

    old_dir.mkdir(parents=True)
    mig.run(str(custom_dir))

    assert old_dir.exists()
    assert not new_dir.exists()


def test_migration_001_conflict_aborts(tmp_path, monkeypatch, caplog):
    """Test that migration aborts if BOTH dirs exist and new has files."""
    mig = importlib.import_module("timetagger.migrations.001_datadir_default_xdg")

    old_dir = tmp_path / "old" / "_timetagger"
    new_dir = tmp_path / "new" / "timetagger"

    monkeypatch.setattr(mig, "get_old_default_dir", lambda: old_dir)
    monkeypatch.setattr(mig, "get_new_default_dir", lambda: new_dir)

    old_dir.mkdir(parents=True)
    new_dir.mkdir(parents=True)
    (new_dir / "jwt.key").touch()

    with caplog.at_level(logging.WARNING):
        mig.run(str(new_dir))

    assert old_dir.exists()
    assert new_dir.exists()
    assert "Skipping automatic migration" in caplog.text


def test_migration_001_new_empty_proceeds(tmp_path, monkeypatch):
    """Test that an accidentally created EMPTY new dir is removed safely to allow move."""
    mig = importlib.import_module("timetagger.migrations.001_datadir_default_xdg")

    old_dir = tmp_path / "old" / "_timetagger"
    new_dir = tmp_path / "new" / "timetagger"

    monkeypatch.setattr(mig, "get_old_default_dir", lambda: old_dir)
    monkeypatch.setattr(mig, "get_new_default_dir", lambda: new_dir)

    old_dir.mkdir(parents=True)
    (old_dir / "jwt.key").touch()
    new_dir.mkdir(parents=True)

    mig.run(str(new_dir))

    assert not old_dir.exists()
    assert (new_dir / "jwt.key").exists()


if __name__ == "__main__":
    run_tests(globals())
