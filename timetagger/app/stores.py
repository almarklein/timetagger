"""
Store records for fast queries.

-----------

When do ranges overlap?

   A1       A2
   |________|
   |________|

        B1       B2
        |________|
        |________|


* Assume/assert that A1 < A2 and B1 < B2
* No ovelap   : A2 <= B1 or  A1 >= B2
* Some overlap: A2 > B1 and A1 < B2
* A fully in B: A1 >= B1 and A2 <= B2
* B fully in A: A1 <= B1 and A2 >= B2

"""

from pscript import this_is_js
from pscript.stubs import Math, Date, JSON, window, console, RawJS


if this_is_js():  # pragma: no cover
    tools = window.tools
    utils = window.utils
    dt = window.dt  # noqa
    random = Math.random

    def to_int(x):
        RawJS(
            """
        x = Number(x)
        if (!isFinite(x)) {
            var e = new  Error("TypeError: Cannot convert to int");
            e.name = "TypeError";
            throw e;
        }
        """
        )
        return Math.floor(x)

    def to_float(x):
        RawJS(
            """
        x = Number(x)
        if (!isFinite(x)) {
            var e = new  Error("TypeError: Cannot convert to int");
            e.name = "TypeError";
            throw e;
        }
        """
        )
        return x

    def to_str(x):
        global String
        s = String(x).slice(0, STR_MAX)
        return s.replace("\r", "").replace("\n", " ").replace("\t", " ").lstrip(' "')

    def to_jsonable(x):
        return x


else:
    from random import random
    from . import dt
    from . import utils

    to_int = int
    to_float = float
    to_str = str
    to_jsonable = lambda x: x

    _dict = dict

    class dict(_dict):  # pragma: no cover
        """A dict in which the items can be get/set as attributes."""

        __reserved_names__ = dir(_dict())
        __slots__ = []

        def __getattribute__(self, key):
            try:
                return object.__getattribute__(self, key)
            except AttributeError:
                if key in self:
                    return self[key]
                else:
                    raise

        def __setattr__(self, key, val):
            if key in dict.__reserved_names__:
                raise AttributeError(
                    "Reserved name, this key can only "
                    + "be set via ``d[%r] = X``" % key
                )
            else:
                self[key] = val

        def __dir__(self):
            names = [k for k in self.keys() if k.isidentifier()]
            return dict.__reserved_names__ + names

        def copy(self):
            return dict(self)

        def clone(self, **kwargs):
            d = dict(self)
            d.update(kwargs)
            return d


_min_heap_bin_size = 2 ** 17  # about 1.5 day


# At the client:
#
# - We specify the fields that an item has.
# - This matches with the server (we ensure this with tests), but the client
#   may be old, so the server may accept more. And send us more.
# - The server will also ignore fields that it does not know, so at the client
#   we don't have to be strict about specific fields on items.
# - But we do check the type of the fields that we know.


# ----- COMMON PART (don't change this comment)

RECORD_SPEC = dict(key=to_str, mt=to_int, t1=to_int, t2=to_int, ds=to_str)
RECORD_REQ = ["key", "mt", "t1", "t2"]

SETTING_SPEC = dict(key=to_str, mt=to_int, value=to_jsonable)
SETTING_REQ = ["key", "mt", "value"]

STR_MAX = 256


# ----- END COMMON PART (don't change this comment)


SPECS = {"records": RECORD_SPEC, "settings": SETTING_SPEC}
REQS = {"records": RECORD_REQ, "settings": SETTING_REQ}


def generate_uid():
    """Generate a unique id in the form of an 8-char string. The value is
    used to uniquely identify the record of one user. Assuming a user
    who has been creating 100 records a day, for 20 years (about 1M records),
    the chance of a collision for a new record is about 1 in 50 milion.
    """
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    n = 8
    nchars = len(chars)  # 52, so 52**8 => 53459728531456 possibilities
    if this_is_js():
        ar = window.Uint32Array(n)
        window.crypto.getRandomValues(ar)
        return "".join([chars[ar[i] % nchars] for i in range(n)])
    else:
        return "".join([chars[int(random() * nchars)] for i in range(n)])


def is_hidden(item):
    """Get whether the given item is hidden."""
    return item.get("ds", "").startswith("HIDDEN")


def make_hidden(item):
    """Mark the given item as hidden."""
    item.ds = "HIDDEN " + item.get("ds", "").split("HIDDEN")[-1].strip()


# %% Sub stores


class BaseStore:
    """Baseclass for the stores."""

    store_type = ""

    def put(self, *items):
        """Push one or more items in the store. This represents creating
        or modifying an item in this client. A copy of the incoming items
        is made to avoid accidentally in-place changes, and records
        can be normalized and even dropped if invalid.
        """
        # Mark as modified
        for i in range(len(items)):
            item = items[i]
            item.st = 0
            item.mt = int(dt.now())
        # Do validation and drops corrupt items
        items = self._validate_items(items)
        items = self._filter_outdated(items)
        items = self._normalize_more(items)
        # Actually store and send to main store to sync with server
        self._put(*items)
        self._datastore._put(self.store_type, *items)

    def _put_received(self, *items):
        """Called by the main store to put items received from the server.
        We never want this to fail or drop items, because it would mean
        inconsistency with the server ...
        """
        # Do validation and drops outdated items
        # items = self._validate_items(items)  -> assume server sends ok data!
        items = self._filter_outdated(items)
        items = self._normalize_more(items)
        # Actually store
        self._put(*items)

    def _validate_items(self, items):
        """Validate all items and returns filtered list of normalized (copied) items."""
        spec = SPECS[self.store_type]
        req = REQS[self.store_type]

        items2 = []  # filtered

        identity = lambda x: x
        for i in range(len(items)):
            item = items[i]
            try:
                # Check that all required keys are present
                keys = item.keys()
                for key in req:
                    if key not in keys:
                        raise ValueError(f"Missing key {key}")
                # Check keys that we know
                item2 = dict()
                for key, val in item.items():
                    normfunc = spec.get(key, identity)
                    item2[key] = normfunc(val)  # Can raise
            except Exception as err:
                print("Item dropped: " + str(err))  # not console.warn because Py
                continue

            items2.append(item2)

        return items2

    def _filter_outdated(self, items):
        items2 = []  # filtered

        # It's crucial for this code to match-up with the server logic to
        # keep correctly synchronized.

        for i in range(len(items)):
            new_item = items[i]
            cur_item = self._items.get(new_item.key, None)
            if cur_item is None:
                # An actual new item
                items2.append(new_item)
            elif new_item.st > 0 and cur_item.st > 0:
                # Both items come from the server. Use what the server does.
                # Note that the server guarantees unique st's (between
                # different versions of an item)
                if new_item.st > cur_item.st:
                    items2.append(new_item)
            elif new_item.mt >= cur_item.mt:
                # Cases include:
                # - we update an item that was updated less than a sec ago
                # - the item that we send to server gets back (with new st)
                # - we get an item from the server that was updated at same mt.
                items2.append(new_item)

        return items2

    def get_by_key(self, key):
        """Get (a copy of) an item given its key, or None."""
        item = self._items.get(key, None)
        if item is not None:
            item = item.copy()
        return item

    def _normalize_more(self, items):
        """Subclasses CAN implement this do additional normalization.
        Don't drop items here!
        """
        return items

    def _put(self, *items):
        """Subclasses MUST implement this."""
        raise NotImplementedError()  # pragma: no cover

    def get_dump(self):
        """Get all items as a list."""
        return list(self._items.values())

    def get_item_count(self):
        """Get the number of items in the store."""
        return len(self._items.keys())


class SettingsStore(BaseStore):
    """Data structure for storing settings."""

    store_type = "settings"

    def __init__(self, datastore):
        self._datastore = datastore  # This object will handle sync and storage
        self._items = {}  # key -> setting

    def create(self, key, value):
        """Create a new setting from a key and value. Does not put it in the store."""
        return dict(key=to_str(key), st=0, mt=int(dt.now()), value=to_jsonable(value))

    def _drop(self, key):
        # Called by datastore to discard items that were not accepted by the server
        self._items.pop(key, None)

    def _put(self, *settings):
        for item in settings:
            self._items[item.key] = item

    def set_color_for_tag(self, tag, color):
        key = "color " + tag
        ob = self.create(key, color)
        self.put(ob)

    def get_color_for_tag(self, tag):
        key = "color " + tag
        ob = self.get_by_key(key)
        if ob is not None and ob.value:
            return ob.value
        else:
            return window.front.COLORS.acc_clr
            # return utils.color_from_name(tag)


class RecordStore(BaseStore):
    """Data structure for storing time records in a way that allows
    efficient updating, syncing, querying records, and calculating
    aggregates. Records that have the same value for t1 and t2 are
    considered running.
    """

    store_type = "records"

    def __init__(self, datastore):
        self._datastore = datastore
        self._items = {}  # key -> record
        self._running_records = {}  # Should be 0, 1, or occasionally maybe a few.
        self._heap = [{}]  # list of layers, each layer is binNr -> stats
        self._heap0_bin2record_keys = {}  # binNr -> dict-of-record-keys (i.e. a set)

    def create(self, t1, t2, ds=""):
        """Create a new record from t1, t2 and maybe ds.
        Does not put it in the store.
        """
        return dict(
            key=generate_uid(),
            st=0,
            mt=int(dt.now()),
            t1=dt.to_time_int(t1),
            t2=dt.to_time_int(t2),
            ds=to_str(ds),
        )

    def tags_from_record(self, record):
        """Get a list of tags from the record.
        If no tags are present, returns a list with one tag: #untagged.
        """
        ds = record.get("ds", "")
        if len(ds) == 0:
            return ["#untagged"]
        tags, _ = utils.get_tags_and_parts_from_string(ds)
        if len(tags) == 0:
            return ["#untagged"]
        else:
            return tags

    def _normalize_more(self, items):
        """Ensure that t1 <= t2"""
        for i in range(len(items)):
            item = items[i]
            item.t1 = min(item.t1, item.t2)
            item.t2 = max(item.t1, item.t2)
        return items

    def _drop(self, key):
        # Called by datastore to discard items that were not accepted by the server

        cur_record = self._items.get(key, None)

        if cur_record is not None:
            self._running_records.pop(key, None)
            self._items.pop(key, None)
            changed_bins = {}  # Poor mans's set
            bin2record_keys = self._heap0_bin2record_keys
            nr1 = cur_record.t1 // _min_heap_bin_size
            nr2 = cur_record.t2 // _min_heap_bin_size
            for nr in range(nr1, nr2 + 1):
                changed_bins[nr] = True
                bin2record_keys[nr].pop(key)
            self._update_bins(0, changed_bins)

    def _put(self, *records):
        """Push records (or record mutations) into the store."""
        PSCRIPT_OVERLOAD = False  # noqa

        # Init
        changed_bins = {}  # Poor mans's set
        bin2record_keys = self._heap0_bin2record_keys

        # Add each record ...
        # We already know that the new record must overwrite the old
        for i in range(len(records)):
            new_record = records[i]
            key = new_record.key
            cur_record = self._items.get(key, None)

            # Store the record in our flat dict
            self._items[key] = new_record

            # Remove cur_record from bins in layer 0
            if cur_record is not None:
                nr1 = cur_record.t1 // _min_heap_bin_size
                nr2 = cur_record.t2 // _min_heap_bin_size
                for nr in range(nr1, nr2 + 1):
                    if bin2record_keys.get(nr, None) is not None:
                        bin2record_keys[nr].pop(key, None)
                        changed_bins[nr] = True
                self._running_records.pop(key, None)

            # Add new_record to bins in layer 0
            # Hidden records are not put in the heap. That way they consume
            # space but not performance.
            if new_record is not None and not is_hidden(new_record):
                nr1 = new_record.t1 // _min_heap_bin_size
                nr2 = new_record.t2 // _min_heap_bin_size
                for nr in range(nr1, nr2 + 1):
                    changed_bins[nr] = True
                    if bin2record_keys.get(nr, None) is None:
                        bin2record_keys[nr] = {}
                    bin2record_keys[nr][key] = True  # don't store actual record
                if new_record.t1 == new_record.t2:
                    self._running_records[key] = new_record

        # Bubble the changes up the heap
        self._update_bins(0, changed_bins)

    def _update_bins(self, level, changed_bins):
        """Update bins of the given layer."""
        PSCRIPT_OVERLOAD = False  # noqa

        # Init
        heaplayer = self._heap[level]
        binsize = _min_heap_bin_size * 2 ** level
        empty_bins = []

        # Iterate over all bins to update
        for nr in changed_bins.keys():
            nr = int(nr)  # oh JS, y u suck so much?
            if heaplayer.get(nr, None) is None:
                heaplayer[nr] = {}
            stats = heaplayer[nr]
            stats.clear()
            if level == 0:
                # Iterate over records
                bin_t1 = binsize * nr
                bin_t2 = binsize * (nr + 1)
                record_keys = self._heap0_bin2record_keys[nr]
                for key in record_keys.keys():
                    record = self._items[key]
                    t1 = max(record.t1, bin_t1)
                    t2 = min(record.t2, bin_t2)
                    tagz = " ".join(self.tags_from_record(record))
                    stats[tagz] = stats.get(tagz, 0) + (t2 - t1)
            else:
                # Iterate over sub-bins
                prevlayer = self._heap[level - 1]
                sub1, sub2 = prevlayer.get(nr * 2, {}), prevlayer.get(nr * 2 + 1, {})
                for substats in (sub1, sub2):
                    for key in substats.keys():
                        stats[key] = stats.get(key, 0) + substats[key]
            # Empty?
            if len(stats.keys()) == 0:
                empty_bins.append(nr)

        # Clean up empty bins
        for nr in empty_bins:
            heaplayer.pop(nr)
            if level == 0:
                self._heap0_bin2record_keys.pop(nr)

        # Next?

        if level > 0 and len(heaplayer.keys()) == 0:
            # Remove this level and all levels above
            while len(self._heap) > level:
                self._heap.pop(-1)
        elif len(heaplayer.keys()) == 1:
            # Remove all levels above here
            while len(self._heap) > level + 1:
                self._heap.pop(-1)
        else:
            # Bubble the changes up the heap
            changed_bins2 = {}
            if len(self._heap) > level + 1:
                for nr in changed_bins.keys():
                    changed_bins2[int(nr) // 2] = True
            else:
                self._heap.append({})  # New layer, update all of it
                for nr in heaplayer.keys():
                    changed_bins2[int(nr) // 2] = True
            self._update_bins(level + 1, changed_bins2)

    def get_running_records(self):
        """Get a list of (copies of) the running records."""
        return [item.copy() for item in self._running_records.values()]

    def get_records(self, t1, t2):
        """Get the records that lay (completely or partially) in the range t1-t2.
        The returned dict contains copies, and can safely be modified. The records
        are not sorted (because the best sorting depends on the use-case).
        """

        # Prepare
        t1, t2 = dt.to_time_int(t1), dt.to_time_int(t2)
        assert len(self._heap[-1].keys()) <= 1
        level = len(self._heap) - 1
        nrs = list(self._heap[-1].keys())
        if len(nrs) == 0 or t1 > t2:
            return {}
        nr = int(nrs[0])

        # Collect records
        records = {}
        self._get_records(t1, t2, level, nr, records)

        # Add running records
        now = dt.now()
        for record in self._running_records.values():
            if now > t1 and record.t1 < t2:
                # it might already be present if t1 < record.t1 < t2
                records[record.key] = record

        # Make copies to prevent in-place mutations
        for key in records.keys():
            records[key] = records[key].copy()

        return records

    def _get_records(self, t1, t2, level, nr, records):
        PSCRIPT_OVERLOAD = False  # noqa

        binsize = _min_heap_bin_size * 2 ** level
        bin_t1 = binsize * (nr + 0.0)
        bin_t2 = binsize * (nr + 1.0)

        # Is this bin (partially) in our range?
        if t2 <= bin_t1 or t1 >= bin_t2:  # A2 <= B1 or A1 >= B2
            # This bin is not in the range at all
            pass
        elif t1 <= bin_t1 and t2 >= bin_t2:  # A1 <= B1 and A2 >= B2
            # This bin is fully inside the requested range
            if level == 0:
                record_keys = self._heap0_bin2record_keys.get(nr, {})
                for key in record_keys.keys():
                    record = self._items[key]
                    if (
                        record.t1 < record.t2
                    ):  # when equal it means the record is running
                        records[key] = self._items[key]
            else:
                subheaplayer = self._heap[level - 1]
                for sub_nr in (nr * 2, nr * 2 + 1):
                    if subheaplayer.get(sub_nr, None) is not None:
                        self._get_records(t1, t2, level - 1, sub_nr, records)
        else:
            # Some part of this bin is inside the requested range, and some is not
            if level == 0:
                record_keys = self._heap0_bin2record_keys.get(nr, {})
                for key in record_keys.keys():
                    record = self._items[key]
                    # A2 > B1 and A1 < B2
                    if record.t1 < record.t2 and t2 > record.t1 and t1 < record.t2:
                        records[key] = record  # only append if *some* overlap
            else:
                subheaplayer = self._heap[level - 1]
                for sub_nr in (nr * 2, nr * 2 + 1):
                    if subheaplayer.get(sub_nr, None) is not None:
                        self._get_records(t1, t2, level - 1, sub_nr, records)

    def get_stats(self, t1, t2):
        """Get the aggregate stats for the time range t1-t2. Returns a dict
        mapping tags to time in seconds.
        """

        # Prepare
        t1, t2 = dt.to_time_int(t1), dt.to_time_int(t2)
        assert len(self._heap[-1].keys()) <= 1
        level = len(self._heap) - 1
        nrs = list(self._heap[-1].keys())
        if len(nrs) == 0 or t1 > t2:
            return {}
        nr = int(nrs[0])

        # Collect stats
        stats = {}
        self._get_stats(t1, t2, level, nr, stats)

        # Post-processing
        now = dt.now()
        for record in self._running_records.values():
            if now > t1 and record.t1 < t2:
                deltat = max(0, min(t2, now) - max(t1, record.t1))
                tagz = " ".join(self.tags_from_record(record))
                stats[tagz] = stats.get(tagz, 0) + deltat
        return stats

    def _get_stats(self, t1, t2, level, nr, stats):
        PSCRIPT_OVERLOAD = False  # noqa

        binsize = _min_heap_bin_size * 2 ** level
        bin_t1 = binsize * (nr + 0.0)
        bin_t2 = binsize * (nr + 1.0)

        # Is this bin (partially) in our range?
        if t2 <= bin_t1 or t1 >= bin_t2:  # A2 <= B1 or A1 >= B2
            # This bin is not in the range at all
            pass
        elif t1 <= bin_t1 and t2 >= bin_t2:  # A1 <= B1 and A2 >= B2
            # This bin is fully inside the requested range
            binstats = self._heap[level].get(nr, {})
            for key in binstats.keys():
                stats[key] = stats.get(key, 0) + binstats[key]
        else:
            # Some part of this bin is inside the requested range, and some is not
            if level == 0:
                record_keys = self._heap0_bin2record_keys.get(nr, {})
                for key in record_keys.keys():
                    record = self._items[key]
                    deltat = min(min(bin_t2, record.t2), t2) - max(
                        max(bin_t1, record.t1), t1
                    )
                    if deltat > 0:  # else no overlap
                        tagz = " ".join(self.tags_from_record(record))
                        stats[tagz] = stats.get(tagz, 0) + deltat
            else:
                subheaplayer = self._heap[level - 1]
                for sub_nr in (nr * 2, nr * 2 + 1):
                    if subheaplayer.get(sub_nr, None) is not None:
                        self._get_stats(t1, t2, level - 1, sub_nr, stats)


# %% Main stores


class BaseDataStore:
    """Class that wraps the specific datastore objects, and the basis
    for performing syncing.
    """

    def __init__(self):
        # Sync stuff
        self._sync_timeout = None
        self._state_timeout = None
        self.reset()
        window.document.addEventListener(
            "visibilitychange", lambda: self.sync_soon(1.0), False
        )

    def reset(self):
        # The sub stores
        self.settings = SettingsStore(self)
        self.records = RecordStore(self)
        # State that can be draw
        self.sync_time = 0, 0
        self.state = ""  # pending, sync, warning, error, ""
        # Sync stuff
        self._to_push = {"settings": {}, "records": {}}
        window.clearTimeout(self._sync_timeout)
        window.clearTimeout(self._state_timeout)
        # Set if off!
        self.sync_soon(1.0)

    def _set_state(self, state, timeout=0):
        """Set the state, now or somewhat later."""
        window.clearTimeout(self._state_timeout)
        self._state_timeout = None
        if timeout > 0:
            self._state_timeout = window.setTimeout(
                self._set_state, timeout * 1000, state
            )
        else:
            self.state = state

    def _put(self, kind, *items):
        """Called by the substores for new/modified items."""
        for i in range(len(items)):
            item = items[i]
            self._to_push[kind][item.key] = item
        self.sync_soon(3)
        self._set_state("pending")

    def sync_soon(self, timeout=10):
        """Invoke a sync action. Cancel the pending sync action."""
        self.sync_time = dt.now(), dt.now() + timeout
        window.clearTimeout(self._sync_timeout)
        self._sync_timeout = window.setTimeout(self._sync_callback, timeout * 1000)

    async def _sync_callback(self):
        self._sync_timeout = None
        self._set_state("sync")
        try:
            await self._sync()
            if window.canvas:
                window.canvas.update()
        finally:
            if self._sync_timeout is None and not window.document.hidden:
                self.sync_soon()  # Post a sync to keep getting updates
        # Reset state, leave current state shown for a bit if _sync() set it.
        if self.state == "sync":
            self._set_state("", 0.25)
        elif self.state != "error":
            self._set_state("", 0.75)

    async def _sync(self):
        pass


class ConnectedDataStore(BaseDataStore):
    """A data store that communicates with the server."""

    def reset(self):
        super().reset()
        self._server_time = 0
        self._last_auth_get = 0
        self._pull_statuses = [0, 0, 0, 0, 0]
        self._auth = window.tools.get_auth_info()
        self._auth_cantuse = None

    def get_auth(self):
        """Get an auth info object that is guaranteed to match the username
        that the store had from the beginning. It gets automatically refreshed
        to include the latest authtoken. Can return None, in which case the store is
        not usable.
        """
        if dt.now() - self._last_auth_get > 1.0:
            self._last_auth_get = dt.now()
            auth = window.tools.get_auth_info()
            if self._auth is None and auth:
                pass  # This can't really happen. If it does, let user reload
            elif auth and auth.username and auth.username == self._auth.username:
                self._auth = auth
            else:
                self._auth = None
            # Check if we've found the auth is not usable (e.g. expiration)
            if self._auth:
                if self._auth_cantuse:
                    self._auth.cantuse = self._auth_cantuse

        return self._auth

    def _log_load(self, where, ob):
        n1, n2, n3 = len(ob.settings), len(ob.records)
        if n1 > 0 or n2 > 0 or n3 > 0:
            console.log("Loading from " + where + ": " + [n1, n2, n3])

    async def _clear_cache(self):
        storage = window.tools.AsyncStorage()
        await storage.clear()

    async def _load_from_cache(self):
        if self._auth and self._auth.username:
            try:
                storage = window.tools.AsyncStorage()
                ob = await storage.getItem(self._auth.username)
                if ob and ob.server_time:
                    self._log_load("cache", ob)
                    self._server_time = ob.server_time
                    self.settings._put_received(*ob.settings)
                    self.records._put_received(*ob.records)
                    for item in ob.settings:
                        if item.st == 0:
                            self._to_push["settings"][item.key] = item
                    for item in ob.records:
                        if item.st == 0:
                            self._to_push["records"][item.key] = item
            except Exception as err:
                console.warn(err)

    async def _save_to_cache(self):
        if self._auth and self._auth.username:
            try:
                dump = {
                    "key": self._auth.username,
                    "server_time": self._server_time,
                    "settings": self.settings.get_dump(),
                    "records": self.records.get_dump(),
                }
                storage = window.tools.AsyncStorage()
                await storage.setItem(dump)
            except Exception as err:
                console.warn(err)

    async def _sync(self):
        # Ignore sync if there is no auth info
        auth = self.get_auth()
        if not auth or auth.cantuse:
            self._set_state("error")
            return
        # Get from local cache?
        if self._server_time == 0:
            await self._load_from_cache()
        # Push to server, then pull
        for kind in ["settings", "records"]:
            await self._push(kind, auth.token)
        await self._pull(auth.token)
        # Save to local cache
        await self._save_to_cache()

    async def _force_reset(self):
        # Set the reset flag at the server. Intended for testing.
        url = tools.build_api_url("forcereset")
        authtoken = self.get_auth().token
        init = dict(method="PUT", headers={"authtoken": authtoken})
        await window.fetch(url, init)

    async def _push(self, kind, authtoken):

        # Take items, only proceed if nonempty
        items = self._to_push[kind]
        if len(items.keys()) == 0:
            return
        self._to_push[kind] = {}

        # Fetch and wait for response
        url = tools.build_api_url(kind)
        init = dict(
            method="PUT",
            body=JSON.stringify(items.values()),
            headers={"authtoken": authtoken},
        )
        try:
            res = await window.fetch(url, init)
        except Exception as err:
            res = dict(status=0, statusText=str(err), text=lambda: "")

        # Process response
        if res.status != 200:
            # The server was not able to process the request, maybe the
            # wifi is down or the server is restarting.
            # Put items back, but don't overwrite if the item was updated again.
            for key, item in items.items():
                self._to_push[kind].setdefault(key, item)
            self._set_state("error")  # is usually less bad than the fail's below
            text = await res.text()
            console.warn(res.status + " (" + res.statusText + ") " + text)
            # Also notify the user for 402 errors
            if res.status == 402 and window.canvas:
                window.canvas.notify_once(text)

        else:
            # Success, but it can still mean that some records failed. In this
            # case these records are likely corrupt, so we delete them, and
            # will get the server's version back when we pull.
            d = JSON.parse(await res.text())
            # d.accepted -> list of ok keys
            for key in d.failed:
                self[kind]._drop(key)
            for err in d.errors:
                self._set_state("warning")
                console.warn(f"Server dropped a {kind}: {err}")

    async def _pull(self, authtoken):

        # Fetch and wait for response
        url = tools.build_api_url("updates?since=" + self._server_time)
        init = dict(method="GET", headers={"authtoken": authtoken})
        try:
            res = await window.fetch(url, init)
        except Exception as err:
            res = dict(status=0, statusText=str(err), text=lambda: "")
        self._pull_statuses.append(res.status)
        self._pull_statuses = self._pull_statuses[-5:]

        # Process response
        if res.status != 200:
            text = await res.text()
            console.warn(res.status + " (" + res.statusText + ") " + text)
            self._set_state("error")  # E.g. Wifi or server down, or 500
            if res.status == 401:
                # Our token is probably expired. There may be local
                # changes that have not yet been pushed, which would
                # be lost if we logout. On the other hand, this may be
                # a lost/stolen device and the user revoked the token.
                # We can distinguish between these cases by determining
                # that the 401 is due to a token seed mismatch (revoked).
                self._auth_cantuse = text
                if "revoked" in text:
                    window.location.href = "../logout"
        else:
            ob = JSON.parse(await res.text())
            if ob.server_time:
                self._log_load("server", ob)
                # Reset?
                if ob.reset:
                    await self._clear_cache()
                    self.reset()
                self._server_time = ob.server_time
                # The odds of something going wrong here are tiny ...
                # but if they happen, we're out of sync with the server :(
                try:
                    self.settings._put_received(*ob.settings)
                except Exception as err:
                    self._set_state("warning")
                    console.error(err)
                    window.alert("Sync error (settings), see dev console for details.")
                try:
                    self.records._put_received(*ob.records)
                except Exception as err:
                    self._set_state("warning")
                    console.error(err)
                    window.alert("Sync error (records), see dev console for details.")

                # Set state to ok if we got new items, and if there were no errors
                if ob.settings or ob.records:
                    if self.state != "warning":
                        self._set_state("ok")


class SandboxDataStore(BaseDataStore):
    """A data store that is empty. Users can import records here and
    play around without breaking anything.
    """

    async def _sync(self):
        """Emulate a sync action."""
        for kind in ["settings", "records"]:
            items = self._to_push[kind].values()
            self._to_push[kind] = {}
            if len(items) > 0:
                await tools.sleepms(200)
                for item in items:
                    item.st = dt.now()
                self[kind]._put_received(*items)
                self._set_state("ok")


class DemoDataStore(BaseDataStore):
    """A data store that is initialized with 5 years worth of randomly
    generated time records.
    """

    def reset(self):
        super().reset()

        nowyear = dt.get_year_month_day(dt.now())[0]
        self._years = list(range(nowyear - 5, nowyear + 1))

        self._create_colors()
        self._create_tags()
        self._create_one_year_of_data(self._years.pop(-1))

    async def _sync(self):
        """Emulate a sync action."""
        for kind in ["settings", "records"]:
            items = self._to_push[kind].values()
            self._to_push[kind] = {}
            if len(items) > 0:
                await tools.sleepms(200)
                for item in items:
                    item.st = dt.now()
                self[kind]._put_received(*items)
                self._set_state("ok")
        # Generate more data, or emulate time for update request
        while len(self._years) > 0:
            self._create_one_year_of_data(self._years.pop(-1))
        else:
            await tools.sleepms(200)

    def _create_colors(self):
        colors = {
            "#admin": "#ED8CC7",
            "#client1": "#607FE0",
            "#client2": "#429270",
        }
        for tag, color in colors.items():
            self.settings.set_color_for_tag(tag, color)

    def _create_tags(self):

        self._tag_groups1 = [
            ["#admin", "#reading"],
            ["#admin", "#traveling"],
        ]

        self._tag_groups2 = [
            ["#client1 #meeting", "#client1 #training", "#client1 #admin"],
            ["#client1 #meeting", "#client1 #code", "#client1 #design"],
            [
                "#client2 #code #writing",
                "#client2 #code",
                "#client2 #code #debugging",
                "#client2 #design",
                "#client2 #meeting",
                "#client2 #admin",
            ],
            [
                "#client2 #code",
                "#client2 #design",
                "#client2 #meeting",
                "#client2 #training",
                "#client2 #admin",
            ],
        ]

    def _create_one_year_of_data(self, y):
        PSCRIPT_OVERLOAD = False  # noqa

        now = dt.now()
        nowyear, nowmonth, nowday = dt.get_year_month_day(dt.now())
        sy = str(y)
        rr = []

        rpd = list(range(3, 9))  # number of records per day

        for m in range(1, 13):
            sm = f"{m:02}"

            # For each month, we select tags from the tag groups,
            # we may not have all, and we may have duplicates.
            tags = []
            for i in range(1):
                tag_group = self._tag_groups1[int(random() * len(self._tag_groups1))]
                for tag in tag_group:
                    tags.append(tag)
            for i in range(2):
                tag_group = self._tag_groups2[int(random() * len(self._tag_groups2))]
                for tag in tag_group:
                    tags.append(tag)

            for d in range(1, 32):
                sd = f"{d:02}"

                # Don't make records in the current future
                if y > nowyear:
                    continue
                elif y == nowyear and m > nowmonth:
                    continue
                elif y == nowyear and m == nowmonth and d > nowday:
                    continue

                # Is this date ok?
                if this_is_js():  # pragma: no cover
                    weekday = Date(f"{sy}-{sm}-{sd}").getDay()  # 0 is Sunday
                    # Put some predictable stuff on today, whatever day it is.
                    if y == nowyear and m == nowmonth and d == nowday:
                        for start, stop, tag in [
                            ("08:51", "09:11", "#admin"),
                            ("09:11", "10:27", "#client1 #meeting"),
                            ("10:29", "11:52", "#client1 #code"),
                            ("12:51", "13:32", "#client1 #code"),
                            ("13:32", "14:28", "#client2 #meeting"),
                            ("14:34", "16:11", "#client2 #design"),
                        ]:
                            t1 = dt.to_time_int(f"{sy}-{sm}-{sd}T{start}:00")
                            t2 = dt.to_time_int(f"{sy}-{sm}-{sd}T{stop}:00")
                            if t2 > now:
                                continue
                            works = ["work", "stuff", "things", "administration"]
                            ds = "Did some " + works[int(random() * len(works))]
                            ds += " " + tag
                            record = self.records.create(t1, t2, ds)
                            record.st = now
                            rr.append(record)
                        continue
                    elif weekday not in (1, 2, 3, 4, 5):
                        continue  # no NaN (invalid date) or weekends
                else:
                    if d > 28:
                        continue  # on Python, during tests

                t1 = dt.to_time_int(f"{sy}-{sm}-{sd}T08:00:00")

                for h in range(rpd[int(random() * len(rpd))]):
                    tag = tags[int(random() * len(tags))]
                    t1 += [0, 10 * 60, 20 * 60][int(random() * 3)]  # pause in secs
                    t2 = t1 + 60 * (60 + int(random() * 120))  # 1-3 hours
                    if t2 > now - 60:
                        break
                    works = ["work", "stuff", "things", "administration"]
                    ds = "Did some " + works[int(random() * len(works))]
                    ds += " " + tag
                    record = self.records.create(t1, t2, ds)
                    record.st = now
                    t1 = t2  # next
                    rr.append(record)

        # Store records
        self.records._put_received(*rr)
