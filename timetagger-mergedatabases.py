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
import logging
import pathlib
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

    parser_list_users = argparser.add_argument_group("users")
    parser_list_users.add_argument(
        "--list-users", action="store_true", help="show all available user databases"
    )

    parser_dump_db = argparser.add_argument_group("dump")
    parser_dump_db.add_argument(
        "--dump", metavar="user", help="dump records of user database"
    )

    parser_merge = argparser.add_argument_group("merge")

    parser_merge.add_argument(
        "--dest",
        metavar="dest_user",
        default="tt_all",
        help="destination user database (default: '%(default)s')",
    )
    parser_merge.add_argument(
        "source_user", nargs="*", help="source user databases (default: <all>)"
    )

    args = argparser.parse_args()
    return args


class MergeDB:
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

    def db_exists(self, db, table=TABLE):
        if db.mtime < 0:
            return False
        if table not in db.get_table_names():
            return False
        return True

    def dump_db_by_username(self, username):
        print(f"username: {username}")
        filename = user2filename(username)
        return self.dump_db_by_filename(filename)

    def dump_db_by_filename(self, filename):
        print(f"filename: {filename}")
        db = ItemDB(filename)
        if not self.db_exists(db):
            print("database: not existant")
            return
        self.dump(db)

    def dump(self, db=None):
        if db is None:
            db = self.target_db
        with db:
            for i in db.select_all(self.TABLE):
                print(i)

    def clear(self):
        with self.target_db:
            self.target_db.delete_table(self.TABLE)
            self.target_db.ensure_table(self.TABLE, *self.INDICES)

    def merge_user_db(self, username):
        if self.target_username is None:
            raise RuntimeError("Target database is not initialized")
        filename = user2filename(username)
        db = ItemDB(filename)
        if not self.db_exists(db):
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
            if self.db_exists(self.target_db, self.TABLE):
                self.target_db.delete_table(self.TABLE)
            self.target_db.rename_table(self.TMP_TABLE, self.TABLE)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(levelname)s %(module)s.%(funcName)s: %(message)s", level=logging.INFO
    )
    logger = logging.getLogger()

    args = get_arguments()
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug(args)

    if args.list_users:
        print(list(MergeDB().get_timetagger_usernames()))
        sys.exit(0)

    if args.dump:
        MergeDB().dump_db_by_username(args.dump)
        sys.exit(0)

    print(f"creating database for user '{args.dest}'")
    print(f"filename: {user2filename(args.dest)}")
    mdb = MergeDB(args.dest)
    mdb.merge(args.source_user)
    # print("resulting db:")
    # mdb.dump()
