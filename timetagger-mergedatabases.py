#!/usr/bin/env python

"""
Merges TimeTagger record tables of multiple users into one user database,
replacing the existing records. Extends the records by user information.

This can be used to create a timetagger view of the records of multiple users.

Author: joerg.steffens@bareos.com

Possible improvements:
* in order to keep the webui fast,
  it would be easy to extend the script to only copy entries
  newer than a specific date.
"""

import argparse
import binascii
import json
import logging
import pathlib
from pprint import pprint
import sys

from itemdb import ItemDB
from timetagger.server._utils import user2filename, filename2user, ROOT_USER_DIR


def get_arguments():
    """setup argument parsing"""
    epilog = """%(prog)s merges TimeTagger record tables of multiple users
    into one user database, replacing the existing records. 
    Every newly generated record is extended by the tag '#user/<username>'.
    This way each record still show to which user it belongs.
    """

    argparser = argparse.ArgumentParser(
        description="Merges TimeTagger record tables of multiple users into one user database.",
        epilog=epilog,
    )
    argparser.add_argument(
        "-d", "--debug", action="store_true", help="enable debugging output"
    )

    subparsers = argparser.add_subparsers()
    parser_users = subparsers.add_parser("users")

    # parser_list_users = argparser.add_argument_group("users")
    parser_users.add_argument(
        "--list", action="store_true", help="show all available user databases"
    )
    parser_users.set_defaults(func=handle_users_command)

    parser_records = subparsers.add_parser("records")
    parser_records.add_argument(
        "--dump", action="store_true", help="dump records of user databases"
    )

    records_merge_group = parser_records.add_argument_group("merging")
    records_merge_group.add_argument(
        "--merge",
        action="store_true",
        help="merge source user database records into dest_user records, overwriting all existing records.",
    )
    records_merge_group.add_argument(
        "--dest",
        metavar="dest_user",
        default="tt_all",
        help="destination user database (default: '%(default)s')",
    )
    parser_records.add_argument(
        "source_user", nargs="*", help="source user (default: <all>)"
    )
    parser_records.set_defaults(parser=parser_records, func=handle_records_command)

    parser_settings = subparsers.add_parser("settings")
    # parser_settings = argparser.add_argument_group("distribute settings")
    parser_settings.add_argument(
        "--dump", action="store_true", help="dump settings from user database"
    )
    parser_settings.add_argument("--settings", help="file", type=argparse.FileType("r"))
    parser_settings.add_argument(
        "dest",
        metavar="dest_user",
        nargs="*",
        help="destination user database (default: '<all_users>')",
    )
    parser_settings.set_defaults(func=handle_settings_command)

    args = argparser.parse_args()
    return args


def itemdb_exists(db, table):
    if db.mtime < 0:
        return False
    if table not in db.get_table_names():
        return False
    return True


class Common:
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


class Settings(Common):
    TABLE = "settings"

    def __init__(self, dest_usernames=None):
        self.logger = logging.getLogger()
        self.dest_usernames = dest_usernames

    def dump(self):
        self.dump_db_by_usernames(self.dest_usernames, self.TABLE)

    def distribute_to_user(self, username, settings):
        db_filename = user2filename(username)
        db = ItemDB(db_filename)
        with db:
            # for key, value in settings.items():
            #     print(f"key: {key}, value: {value}")
            #     db.put_one(self.TABLE, key=key, value=value)
            for row in settings:
                print(f"row: {row}")
                db.put(self.TABLE, row)

    def distribute(self, settings):
        # for key, value in settings.items():
        #     print(f"key: {key}, value: {value}")
        for username in self.dest_usernames:
            print(f"distribute settings to user '{username}'")
            self.distribute_to_user(username, settings)


class MergeDB(Common):
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

    def get_timetagger_usernames(self):
        logger = logging.getLogger()
        logger.debug("ROOT_USER_DIR: %s", ROOT_USER_DIR)
        ignore_usernames = ["defaultuser", self.target_username]
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

    def dump_db_by_usernames(self, users):
        if not users:
            users = list(self.get_timetagger_usernames())
        super().dump_db_by_usernames(users, self.TABLE)

    def clear(self):
        with self.target_db:
            self.target_db.delete_table(self.TABLE)
            self.target_db.ensure_table(self.TABLE, *self.INDICES)

    def merge_user_db(self, username):
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
                    self.target_db.put(self.TMP_TABLE, row)

    def merge(self, users=None):
        if not users:
            users = list(self.get_timetagger_usernames())
        for username in users:
            print(f"merging user records of '{username}'")
            self.merge_user_db(username)
        with self.target_db:
            # delete running timers
            self.target_db.delete(self.TMP_TABLE, "t1 = t2")
        with self.target_db:
            if itemdb_exists(self.target_db, self.TABLE):
                self.target_db.delete_table(self.TABLE)
            self.target_db.rename_table(self.TMP_TABLE, self.TABLE)


def handle_users_command(args):
    # if args.list:
    # currently, there is only the list subcommand:
    print(list(MergeDB().get_timetagger_usernames()))
    sys.exit(0)


def handle_settings_command(args):
    settings = Settings(args.dest)
    if args.settings:
        settings_data = json.load(args.settings)
        pprint(settings_data)
        settings.distribute(settings_data)
    if args.dump:
        settings.dump()
    sys.exit(0)


def handle_records_command(args):
    if args.dump:
        MergeDB().dump_db_by_usernames(args.source_user)
        sys.exit(0)
    if args.merge:
        print(f"creating database for user '{args.dest}'")
        print(f"filename: {user2filename(args.dest)}")
        mdb = MergeDB(args.dest)
        mdb.merge(args.source_user)
        # print("resulting db:")
        # mdb.dump()
        sys.exit(0)
    args.parser.print_help()


if __name__ == "__main__":
    logging.basicConfig(
        format="%(levelname)s %(module)s.%(funcName)s: %(message)s", level=logging.INFO
    )
    logger = logging.getLogger()

    args = get_arguments()
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug(args)

    args.func(args)
    sys.exit(0)
