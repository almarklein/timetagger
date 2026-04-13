import shutil
import logging
from pathlib import Path
import platformdirs


def get_new_default_dir() -> Path:
    return platformdirs.user_data_path(
        appname="timetagger", appauthor="Klein"
    ).resolve()


def get_old_default_dir() -> Path:
    return (Path.home() / "_timetagger").resolve()


def run(datadir: str):
    new_default = get_new_default_dir()
    old_default = get_old_default_dir()

    current_cfg = Path(datadir).expanduser().resolve()

    # skip if user is using some custom non-default path
    if current_cfg != new_default:
        return

    # skip if there is no old directory to migrate
    if not old_default.exists() or not old_default.is_dir():
        return

    # handle conflicts if the new directory already exists
    if new_default.exists():
        if any(new_default.iterdir()):
            logging.warning(
                f"Notice: Both old ({old_default}) and new ({new_default}) "
                "data directories exist. Skipping automatic migration to prevent overwriting."
            )
            return
        else:
            # if it's completely empty, safely remove it to allow the move
            new_default.rmdir()

    try:
        logging.info(
            f"Migrating data from {old_default} to standard location: {new_default}..."
        )
        new_default.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_default), str(new_default))
        logging.info("Data directory migration successful.")
    except Exception as e:
        logging.error(f"Failed to migrate data directory: {e}")
