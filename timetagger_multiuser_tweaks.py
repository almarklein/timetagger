#!/usr/bin/env python3

"""
Some utilities to help running TimeTagger in a multi-user environment.

Examples:
* multiuser_tweaks.py records --merge --dest newuser
  * merges TimeTagger record tables of multiple users into one user database,
    replacing the existing records. Extends the records by user information.
    This can be used to create a timetagger view of the records of multiple users.
* multiuser_tweaks.py settings --settings settings.json
  * copy settings from a JSON file to the users settings database tables.

Author: joerg.steffens@bareos.com
"""

import argparse
import binascii
import json
import logging
import pathlib
from pprint import pprint, pformat  # noqa
import sys
import time

from itemdb import ItemDB
from timetagger.server._utils import user2filename, filename2user, ROOT_USER_DIR


def setup_parser():
    """setup argument parsing"""
    epilog = """%(prog)s is a helper tool for TimeTagger in multi-user environments.
    TimeTagger uses a separate Sqlite database per user.
    This tool directly accesses the databases and offers to manipulate them.
    Especially it can merge the records of multiple users
    into one user database, replacing the existing records.
    Every newly generated record is extended by the tag '#user/<username>'.
    This way each record still show to which user it belongs.
    """

    argparser = argparse.ArgumentParser(
        description="Perform actions on TimeTagger databases.",
        epilog=epilog,
    )
    argparser.add_argument(
        "-d", "--debug", action="store_true", help="enable debugging output"
    )

    subparsers = argparser.add_subparsers()

    # users
    parser_users = subparsers.add_parser("users")
    parser_users.add_argument(
        "--list", action="store_true", help="show all available user databases"
    )
    parser_users.set_defaults(parser=parser_users, func=handle_users_command)

    # records
    parser_records = subparsers.add_parser(
        "records",
        description="Perform action on the records tables of TimeTagger databases.",
    )
    parser_records.add_argument(
        "--dump", action="store_true", help="dump records of user databases"
    )
    records_merge_group = parser_records.add_argument_group("merging")
    records_merge_group.add_argument(
        "--merge",
        action="store_true",
        help="merge source user database records into dest_user records, overwriting all existing records",
    )
    records_merge_group.add_argument(
        "--dest",
        metavar="dest_user",
        default="tt_all",
        help="destination user database (default: '%(default)s')",
    )
    records_merge_group.add_argument(
        "--replace",
        action="append",
        help="Replace text entries. The format is '/original_text/replacement_text/'. You can use other separators instead of '/'. This parameter can be given multiple times.",
    )
    parser_records.add_argument(
        "source_user", nargs="*", help="source user (default: <all>)"
    )
    parser_records.set_defaults(parser=parser_records, func=handle_records_command)

    # settings
    parser_settings = subparsers.add_parser(
        "settings",
        description="Perform action on the settings tables of TimeTagger databases.",
    )
    parser_settings.add_argument(
        "--dump", action="store_true", help="dump settings from user databases"
    )
    parser_settings.add_argument(
        "--source",
        help='copy settings from JSON file into user settings databases. Format: { "key1": "value1", "key2": "value2" [, ...] }',
        type=argparse.FileType("r"),
        metavar="<filename.json>",
    )
    parser_settings.add_argument(
        "--force", action="store_true", help="overwrite existing user settings"
    )
    parser_settings.add_argument(
        "dest",
        metavar="dest_user",
        nargs="*",
        help="destination user database (default: '<all_users>')",
    )
    parser_settings.set_defaults(parser=parser_settings, func=handle_settings_command)

    return argparser


def itemdb_exists(db, table):
    if db.mtime < 0:
        return False
    if table not in db.get_table_names():
        return False
    return True


def get_translation_table(replace):
    if replace is None:
        return None
    table = {}
    for i in replace:
        sep = i[0]
        strings = i.split(sep)
        if len(strings) != 4 or len(strings[0]) != 0 or len(strings[3]) != 0:
            raise ValueError(
                f"Replacement string ('{i}') has an invalid form. Use '/original_text/replacement_text/'. You can use other separators instead of '|'."
            )
        table[strings[1]] = strings[2]
    return table


class TimeTaggerDB:
    def get_timetagger_usernames(self, exclude_users=None):
        logger = logging.getLogger()
        logger.debug("ROOT_USER_DIR: %s", ROOT_USER_DIR)
        ignore_usernames = ["defaultuser"]
        if exclude_users:
            ignore_usernames += exclude_users
        for filename in pathlib.Path(ROOT_USER_DIR).glob("*.db"):
            try:
                username = filename2user(filename)
                if username in ignore_usernames:
                    logger.debug("skipping username '%s'", username)
                else:
                    logger.debug("db: %s, user: %s", filename, username)
                    yield username
            except binascii.Error:
                logger.warning(
                    "failed to extract username from filename '%s', skipped.", filename
                )

    def dump_db_by_usernames(self, usernames, table):
        for username in usernames:
            self.dump_db_by_username(username, table)

    def dump_db_by_username(self, username, table):
        print()
        print(f"username: {username}")
        filename = user2filename(username)
        return self.dump_db_by_filename(filename, table)

    def dump_db_by_filename(self, filename, table):
        print(f"filename: {filename}")
        db = ItemDB(filename)
        if not itemdb_exists(db, table):
            print("database: not existant")
            return
        self.dump_db(db, table)

    def dump_db(self, db, table):
        with db:
            for i in db.select_all(table):
                print(i)


class Settings(TimeTaggerDB):
    TABLE = "settings"

    def __init__(self, dest_usernames=None):
        self.logger = logging.getLogger()
        if dest_usernames:
            self.dest_usernames = dest_usernames
        else:
            self.dest_usernames = self.get_timetagger_usernames()

    def dump(self):
        self.dump_db_by_usernames(self.dest_usernames, self.TABLE)

    def distribute_to_user(self, username, settings, force):
        db_filename = user2filename(username)
        db = ItemDB(db_filename)
        if not itemdb_exists(db, self.TABLE):
            print("  skipped, database (table) does not exists")
            return
        now = int(time.time())
        with db:
            for key, value in settings.items():
                print(f"  '{key}': ", end="")
                result = db.select_one(self.TABLE, "key = ?", key)
                if key == "tag_presets":
                    current_set = set()
                    if result:
                        current_set = set(result.get("value"))
                    new_set = set(value)
                    if new_set <= current_set:
                        print("skipped (values already set)")
                        continue
                    print("adding: ", list(new_set - current_set))
                    value = list(current_set | new_set)
                    db.put_one(self.TABLE, key=key, value=value, st=now, mt=now)
                elif result and not force:
                    print("skipped (already set)")
                else:
                    print(value)
                    db.put_one(self.TABLE, key=key, value=value, st=now, mt=now)

    def distribute(self, settings, force):
        # for key, value in settings.items():
        #     print(f"key: {key}, value: {value}")
        for username in self.dest_usernames:
            print(f"distribute settings to user '{username}'")
            self.distribute_to_user(username, settings, force)


class Records(TimeTaggerDB):
    """Merge multiple ItemDB records tables"""

    TABLE = "records"
    TMP_TABLE = "records_new"
    # INDICES = ("!key", "st", "t1", "t2")
    # add user column. Not used by timetagger, but simply ignored.
    INDICES = ("!key", "st", "t1", "t2", "user")

    def __init__(self, target_username=None):
        self.logger = logging.getLogger()
        self.target_username = target_username
        if self.target_username:
            self.target_db_filename = user2filename(target_username)
            self.target_db = ItemDB(self.target_db_filename)
            self.target_db.ensure_table(self.TMP_TABLE, *self.INDICES)

    def dump_db_by_usernames(self, users):
        if not users:
            users = list(self.get_timetagger_usernames())
        super().dump_db_by_usernames(users, self.TABLE)

    def clear(self):
        with self.target_db:
            self.target_db.delete_table(self.TABLE)
            self.target_db.ensure_table(self.TABLE, *self.INDICES)

    def merge_user_db(self, username, replace_dict):
        if self.target_username is None:
            raise RuntimeError("Target database is not initialized")
        filename = user2filename(username)
        db = ItemDB(filename)
        if not itemdb_exists(db, self.TABLE):
            raise RuntimeError(
                f"Accessing database {filename} failed: no such file or table ({self.TABLE})"
            )
        with self.target_db:
            with db:
                for row in db.select_all(self.TABLE):
                    try:
                        if "#user/" not in row["ds"]:
                            row["ds"] += f" #user/{username}"
                    except KeyError:
                        row["ds"] = f"#user/{username}"
                    row["user"] = username
                    if replace_dict:
                        for orig, replacement in replace_dict.items():
                            row["ds"] = row["ds"].replace(orig, replacement)
                    self.target_db.put(self.TMP_TABLE, row)

    def merge(self, users=None, replace=None):
        if not users:
            users = list(self.get_timetagger_usernames([self.target_username]))
        replace_dict = get_translation_table(replace)
        if replace_dict:
            print("replacements: {}".format(pformat(replace_dict)))
        for username in users:
            print(f"merging user records of '{username}'")
            self.merge_user_db(username, replace_dict)
        with self.target_db:
            # delete running timers
            self.target_db.delete(self.TMP_TABLE, "t1 = t2")
        with self.target_db:
            if itemdb_exists(self.target_db, self.TABLE):
                self.target_db.delete_table(self.TABLE)
            self.target_db.rename_table(self.TMP_TABLE, self.TABLE)


def handle_users_command(args):
    # currently, there is only the list subcommand:
    print(list(TimeTaggerDB().get_timetagger_usernames()))


def handle_settings_command(args):
    settings = Settings(args.dest)
    if args.source:
        settings_data = json.load(args.source)
        # pprint(settings_data)
        settings.distribute(settings_data, args.force)
    elif args.dump:
        settings.dump()
    else:
        args.parser.print_help()


def handle_records_command(args):
    if args.dump:
        Records().dump_db_by_usernames(args.source_user)
        sys.exit(0)
    elif args.merge:
        print(f"creating database for user '{args.dest}'")
        print(f"filename: {user2filename(args.dest)}")
        records = Records(args.dest)
        records.merge(args.source_user, args.replace)
    else:
        args.parser.print_help()


if __name__ == "__main__":
    logging.basicConfig(
        format="%(levelname)s %(module)s.%(funcName)s: %(message)s", level=logging.INFO
    )
    logger = logging.getLogger()

    parser = setup_parser()
    args = parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug(args)

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
