#!/usr/bin/env python3

"""
With this little script there shall be some kind of bulk editing for
records, as long as Timetagger does not impemented it natively.

So far this bulk editing options are available:
- changing color for multiple tags in a bulk
- changing priority of multiple tags in a bulk
- changing targets of multiple tags in a bulk
- deleting multiple tags in a certain time range in a bulk

Examples:
* timetagger_bulk_edit.py USERNAME -c/--colorize STRING|FILE COLOR
  * Colorizes the tags given as a string or a file in th given color
    (also as a string) for th database of the given username.
    USERNAME: the username as a string
    STRING:   a string containing comma seperated tags; with or witout
              the hash sign and with or without whitespace.
              E.g.: "#tag1,tag2, #tag3"
    FILE:     instead of the string there can also be a file containing
              the tags as a similar comma sepaated string or as newlines.
    COLOR:    The color with or without the hash sign: "7272ab" or "#7272ab"

* timetagger_bulk_edit.py USERNAME -dr/--delete-range FROM TO
  * FROM:     The from unix time stamp or date-string of the records to delete.
              If set to -1, only the TO argument will be used and every dataset
              "before" that will be deleted.
    TO:       The unix time stamp or date-string for the records to delete,
              while this is the ranges top of the date. If this will be set to -1,
              the FROM unix time stamp will be used only and thus all
              records from this time stamp on will be deleted.
              If both arguments are -1 it basically will remove ALL
              RECORDS !!!!
    date format: can be the following:
        - string can be unix timestamp itself
        - string can be YYYY-MM-DDTHH:MM:SS like "2024-04-01T01:23:45"
        - string can be YYYY-MM-DD like "2024-04-01"
            this gets translated to the start of the day for FROM and
            to the end of the day for TO
    deleting items:
        Timetagge follows the convention of making records hidden instead of really
        removing them from the database. This is done by appending the description
        with "HIDDEN ". If you really want to "completely delete" the records as
        well, you might consider using SQLite3 in the terminal and remove datasets
        in the "records" table, which contain "HIDDEN" in the column "_ob". Yet
        consider that any client might still have the records in its local
        database. Maybe clearing this as well (thus also the locally stored settings)
        might help then.

* timetagger_bulk_edit.py USERNAME -dt/--delete-tag TAGS
    * TAGS:   The given tags will be used to determine, which records wil be
              deleted. Unlike the colorizing it's no bulk for "delete this entries
              with this tag, then delete entries with this tag, ...", but rather
              a logical AND. So: "delete entries, which have this tag AND this tag ...".
              Also consider the deletion convention: Timetagger does not really
              delete entries, yet marks them hidden by appending "HIDDEN " to the
              description. See "deleting items" above for more infos about that.
    ATTENTION:  If only one tag is given, records will also be deleted, if they
                contain this tag AND OTHERS!!


Thanks to joerg.steffens@bareos.com from whichs multiuser_tweaks.py
script I learned some things and used code snippets as well!

Author: Manuel Senfft (info@tagirijus.de)
"""

import argparse
import datetime
from itemdb import ItemDB
import json
import logging
import os
import pathlib
import time

from timetagger.server._utils import user2filename, filename2user, ROOT_USER_DIR


def setup_parser():
    argparser = argparse.ArgumentParser(
        description=(
            'Bulk editor for Timetagger SQLite databases.'
        )
    )


    argparser.add_argument(
        'username',
        default='_LIST',
        help='The username. Use "_LIST" as the username to get a list of all usernames.'
    )

    argparser.add_argument(
        '-d',
        '--debug',
        action='store_true',
        help='enable debugging output'
    )

    argparser.add_argument(
        '-c',
        '--colorize',
        nargs=2,
        help='Colorizes the given tags with the given color: STRING|FILE COLOR.'
    )

    argparser.add_argument(
        '-p',
        '--priority',
        nargs=2,
        help='Set priority for the given tags with the given priority: STRING|FILE PRIORITY.'
    )

    argparser.add_argument(
        '-t',
        '--targets',
        nargs=2,
        help='Set targets for the given tags with the given targets: STRING|FILE TARGETS.'
    )

    argparser.add_argument(
        '-dr',
        '--delete-range',
        nargs=2,
        help=(
            'Delete records between FROM and TO (unix timestamps). When setting one or both to -1,'
            + ' all records before, after or even ALL records will be deleted!'
            + ' So use it like -d FROM TO; e.g. -d 1713520609 -1 will remove all entries '
            + '  beginning from 19th April of 2024.'
        )
    )

    argparser.add_argument(
        '-dt',
        '--delete-tags',
        nargs=1,
        help=(
            'Delete records which have all the given tags. Can be a file or a string,'
            + ' e.g. "-dt #clientA,#projectB'
        )
    )

    return argparser


class BulkEditor:
    """BulkEditor contains some basic functions/methods"""

    def __init__(self, dest_username=None):
        self.logger = logging.getLogger()
        self.dest_username = dest_username
        self.db = self.get_db_by_username(self.dest_username)

    def get_timetagger_usernames(self, exclude_users=None):
        self.logger.debug("ROOT_USER_DIR: %s", ROOT_USER_DIR)
        ignore_usernames = ["defaultuser"]
        if exclude_users:
            ignore_usernames += exclude_users
        for filename in pathlib.Path(ROOT_USER_DIR).glob("*.db"):
            try:
                username = filename2user(filename)
                if username in ignore_usernames:
                    self.logger.debug("skipping username '%s'", username)
                else:
                    self.logger.debug("db: %s, user: %s", filename, username)
                    yield username
            except binascii.Error:
                self.logger.warning(
                    "failed to extract username from filename '%s', skipped.", filename
                )

    def get_list_from_string_or_file(self, str_or_file):
        # try to load content from file, if it's a file
        if os.path.exists(str_or_file):
            with open(str_or_file, 'r') as myfile:
                data = myfile.read()
        else:
            data = str_or_file

        # split the given content by comma or newlines
        if ',' in data:
            # here I first remove any hash signs and add them new.
            # that way the given strings do not have to have hash
            # signs yet they may have.
            return [f'#{i.strip().replace("#", "")}' for i in data.split(',') if i.strip()]
        elif '\n' in data:
            return [f'#{i.strip().replace("#", "")}' for i in data.splitlines() if i.strip()]
        else:
            return [f'#{data.replace("#", "")}']

    def get_db_by_username(self, username):
        filename = user2filename(username)
        self.logger.debug(f'Using file: {filename}')
        return ItemDB(filename)


class Settings(BulkEditor):

    def __init__(self, dest_username=None):
        super(Settings, self).__init__(dest_username)
        self.TABLE = "settings"

    def get_settings_item_or_create_new(self, key):
        selected = self.db.select_one(self.TABLE, 'key = ?', key)
        if selected:
            return selected
        else:
            now = int(time.time())
            # as of 2024-04-24 this seem to be some kind of
            # basic settings item in the table. tags get the
            # color #DEAA22 by default (this yellow one) and
            # priority is 0, while no targets are set.
            # maybe I have to update this at some point, when
            # e.g. tags can get more settings values or so.
            return {
                'key': key,
                'value': {
                    'targets': {},
                    'priority': 0,
                    'color': '#DEAA22'
                },
                'st': now,
                'mt': now
            }

    def modify_tags(self, tags, color=None, priority=None, targets=None):
        """
        This method is for the following modification
        options of a tag via the settings table:
        - colorizing
        - setting a priority
        - setting a targets
        """
        tags = self.get_list_from_string_or_file(tags)

        with self.db:
            for tag in tags:
                # gettint the item and modify it, or get a blank new one
                key = 'taginfo ' + tag
                item = self.get_settings_item_or_create_new(key)
                item = self.modify_single_tag(item, color=color, priority=priority, targets=targets)
                self.db.put(self.TABLE, item)

    def modify_single_tag(self, item, color=None, priority=None, targets=None):
        now = int(time.time())
        item['st'] = now
        if color is not None:
            color = f'#{color.replace("#", "")}'
            self.logger.debug(f'Setting color to: {str(color)} for {item["key"].replace("taginfo ", "")}')
            item['value']['color'] = color
        if priority is not None:
            self.logger.debug(f'Setting priority to: {str(priority)} for {item["key"].replace("taginfo ", "")}')
            item['value']['priority'] = priority
        if targets is not None:
            self.logger.debug(f'Setting targets to: {str(targets)} for {item["key"].replace("taginfo ", "")}')
            item['value']['targets'] = json.loads(targets)
        return item


class Records(BulkEditor):

    def __init__(self, dest_username=None):
        super(Records, self).__init__(dest_username)
        self.TABLE = "records"

    def get_unix_timestamp_from_string(time_string, end_of_day_on_missing_time=False):
        try:
            # maybe it's a unix timestamp given as a string already
            unix_time = int(time_string)
            return unix_time
        except ValueError:
            try:
                # it's maybe in the format YYYY-MM-DDTHH:MM:SS
                dt = datetime.datetime.strptime(time_string, "%Y-%m-%dT%H:%M:%S")
                return int(dt.timestamp())
            except ValueError:
                try:
                    # it's maybe (hopefully at least) in the format YYYY-MM-DD
                    dt = datetime.datetime.strptime(time_string, "%Y-%m-%d")
                    if end_of_day_on_missing_time:
                        dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
                    return int(dt.timestamp())
                except ValueError as e:
                    return time_string

    def delete_records_in_range(self, from_unix_timestamp, to_unix_timestamp):
        """
        This method gets the records in the given time range and
        then uses the found items array with the delete_records()
        method.
        """
        from_unix_timestamp = Records.get_unix_timestamp_from_string(from_unix_timestamp)
        to_unix_timestamp = Records.get_unix_timestamp_from_string(to_unix_timestamp, True)

        all_items = self.db.select_all(self.TABLE)
        items = []

        # basically delete all entries ... :'-)
        if from_unix_timestamp == -1 and to_unix_timestamp == -1:
            self.logger.debug(f'Deleting records in time range: ALL records!')
            items = all_items
        # delete entries from a given time
        elif from_unix_timestamp != -1 and to_unix_timestamp == -1:
            from_date = datetime.datetime.fromtimestamp(from_unix_timestamp)
            self.logger.debug(
                f'Deleting records in time range: since {from_date.strftime("%Y-%m-%d %H:%M:%S")}!'
            )
            items = [i for i in all_items if i['t1'] > from_unix_timestamp]
        # delete entries to a given time
        elif from_unix_timestamp == -1 and to_unix_timestamp != -1:
            to_date = datetime.datetime.fromtimestamp(to_unix_timestamp)
            self.logger.debug(
                f'Deleting records in time range: till {to_date.strftime("%Y-%m-%d %H:%M:%S")}!'
            )
            items = [i for i in all_items if i['t2'] < to_unix_timestamp]
        # delete entries between a given time range
        elif from_unix_timestamp != -1 and to_unix_timestamp != -1:
            from_date = datetime.datetime.fromtimestamp(from_unix_timestamp)
            to_date = datetime.datetime.fromtimestamp(to_unix_timestamp)
            self.logger.debug(
                f'Deleting records in time range: from {from_date.strftime("%Y-%m-%d %H:%M:%S")} to {to_date.strftime("%Y-%m-%d %H:%M:%S")}!'
            )
            items = [i for i in all_items if i['t1'] > from_unix_timestamp and i['t2'] < to_unix_timestamp]

        self.delete_records(items)

    def description_has_tags(ds, tags):
        """
        With this method you can check the given description
        string and return if all the given tags in the array
        are in the string.
        """
        for tag in tags:
            if tag not in ds:
                return False
        return True

    def delete_records_with_tags(self, tags):
        """
        Delete all entries, which have the given tags. The argument
        here can be a string, containing comma seperated tags or it
        can be a file.
        """
        tags = self.get_list_from_string_or_file(tags)

        all_items = self.db.select_all(self.TABLE)
        items = []

        self.logger.debug(
            f'Deleting records which have all these tags: {", ".join(tags)}!'
        )

        for item in all_items:
            if Records.description_has_tags(item['ds'], tags):
                items.append(item)

        self.delete_records(items)


    def delete_records(self, items):
        """
        This method gets items and deletes them and writes it back
        into the database. Writing, because Timetagge does not
        really deletes records, but marks them as hidden by
        appending the description with "HIDDEN ".
        """
        with self.db:
            for item in items:
                # line is basically copied from timetaggers stores.py
                item['ds'] = "HIDDEN " + item.get("ds", "").split("HIDDEN")[-1].strip()
                now = int(time.time())
                item['st'] = now
                self.db.put(self.TABLE, item)



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

    if args.username == '_LIST':
        print(f'Users: {", ".join(BulkEditor.get_timetagger_usernames())}')
        exit()

    if args.colorize:
        settings = Settings(args.username)
        settings.modify_tags(args.colorize[0], color=args.colorize[1])

    if args.priority:
        settings = Settings(args.username)
        settings.modify_tags(args.priority[0], priority=args.priority[1])

    if args.targets:
        settings = Settings(args.username)
        settings.modify_tags(args.targets[0], targets=args.targets[1])

    if args.delete_range:
        records = Records(args.username)
        records.delete_records_in_range(args.delete_range[0], args.delete_range[1])

    if args.delete_tags:
        records = Records(args.username)
        records.delete_records_with_tags(args.delete_tags[0])
