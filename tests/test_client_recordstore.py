from _common import run_tests
from timetagger.app.stores import RecordStore, make_hidden


class DataStoreStub:
    def _put(self, kind, *items):
        assert kind == "records"


def test_record_store1():
    datastore = DataStoreStub()
    rs = RecordStore(datastore)

    # Nothing in there
    assert len(rs._heap) == 1 and len(rs._heap[0].keys()) == 0

    # We can get stats
    assert len(rs.get_records(0, 1e15)) == 0
    assert len(rs.get_stats(0, 1e15).keys()) == 0

    rs.put(rs.create("2018-04-23 15:00:00", "2018-04-23 16:00:00", "#p1"))
    rs.put(rs.create("2018-04-23 17:00:00", "2018-04-23 17:30:00", "#p1"))

    # Two nearby entries, which we picked to be inside a single bin (bins are about 1.5 day wide)
    assert len(rs._heap[-1].keys()) == 1
    assert len(rs._heap) in (1, 2)  # Exact value depends on timezone
    assert len(rs.get_records(0, 1e15)) == 2
    assert rs.get_stats(0, 1e15) == {"#p1": 90 * 60}

    # Add very early records
    rs.put(rs.create("2014-01-12 14:00:00", "2014-01-12 17:30:00", "#p2"))

    # Now need a steep heap
    assert len(rs._heap[-1].keys()) == 1
    assert len(rs._heap) == 12
    assert len(rs.get_records(0, 1e15)) == 3
    assert rs.get_stats(0, 1e15) == {"#p1": 90 * 60, "#p2": 210 * 60}

    # Sample 2014 and 2018 seperately
    assert len(rs.get_records("2014-01-01 00:00:00", "2015-01-01 00:00:00")) == 1
    assert len(rs.get_records("2018-01-01 00:00:00", "2019-01-01 00:00:00")) == 2
    assert rs.get_stats("2014-01-01 00:00:00", "2015-01-01 00:00:00") == {
        "#p2": 210 * 60
    }
    assert rs.get_stats("2018-01-01 00:00:00", "2019-01-01 00:00:00") == {
        "#p1": 90 * 60
    }

    # Now move the record from 2014 to 2018
    key = list(rs.get_records("2014-01-01 00:00:00", "2015-01-01 00:00:00").values())[
        0
    ].key
    record = rs.create("2018-04-22 14:00:00", "2018-04-22 17:30:00", "#p2")
    record.key = key
    rs.put(record)

    assert len(rs._heap[-1].keys()) == 1
    assert len(rs._heap) in (1, 2)
    assert len(rs.get_records(0, 1e15)) == 3

    assert rs.get_stats("2014-01-01 00:00:00", "2015-01-01 00:00:00") == {}
    assert rs.get_stats("2018-01-01 00:00:00", "2019-01-01 00:00:00") == {
        "#p1": 90 * 60,
        "#p2": 210 * 60,
    }

    # Now remove all records
    for record in rs.get_records(0, 1e15).values():
        rs.put(record.clone(ds="HIDDEN"))

    # Verify that records are gone from the heap
    assert len(rs._heap) == 1
    assert len(rs._heap[0].keys()) == 0
    assert len(rs._heap0_bin2record_keys.keys()) == 0
    # But not from the pool of records
    assert len(rs._items.keys()) == 3


def test_record_store_untagged():
    datastore = DataStoreStub()
    rs = RecordStore(datastore)

    # Nothing in there
    assert len(rs._heap) == 1 and len(rs._heap[0].keys()) == 0

    # We can get stats
    assert len(rs.get_records(0, 1e15)) == 0
    assert len(rs.get_stats(0, 1e15).keys()) == 0

    rs.put(rs.create("2018-04-23 15:00:00", "2018-04-23 16:00:00", ""))
    rs.put(rs.create("2018-04-23 17:00:00", "2018-04-23 17:30:00", "foo"))

    assert rs.get_stats(0, 1e15) == {"#untagged": 90 * 60}

    rs.put(rs.create("2018-04-24 17:00:00", "2018-04-24 17:30:00", "#foo"))

    assert rs.get_stats(0, 1e15) == {"#untagged": 90 * 60, "#foo": 30 * 60}


def test_record_spanning_multiple_bins():
    datastore = DataStoreStub()
    rs = RecordStore(datastore)

    # Make a record of 5 days, which, with 1.5 day bins should span at least 3 bins
    r1 = rs.create("2018-04-20 00:00:00", "2018-04-25 00:00:00", "#p3")
    rs.put(r1)

    assert len(rs._heap[-1].keys()) == 1
    assert len(rs._heap) == 3
    assert len(rs._heap[0]) == 4
    assert len(rs.get_records(0, 1e15)) == 1
    assert rs.get_stats(0, 1e15) == {"#p3": 5 * 24 * 60 * 60}

    # Another record, that has overlap
    r2 = rs.create("2018-04-23 00:00:00", "2018-04-28 00:00:00", "#p4")
    rs.put(r2)

    assert len(rs._heap[-1].keys()) == 1
    assert len(rs._heap) == 6
    assert len(rs._heap[0]) == 6
    assert len(rs.get_records(0, 1e15)) == 2
    assert rs.get_stats(0, 1e15) == {"#p3": 5 * 24 * 60 * 60, "#p4": 5 * 24 * 60 * 60}

    # Change project of the latter to the same as the first
    r2_ = rs.create("2018-04-23 00:00:00", "2018-04-28 00:00:00", "#p3")
    r2_.key = r2.key
    rs.put(r2_)

    assert rs.get_stats(0, 1e15) == {"#p3": 2 * 5 * 24 * 60 * 60}

    # Add a tiny record somewhere in there too (10 seconds)
    r3 = rs.create("2018-04-24 00:00:00", "2018-04-24 00:00:10", "#p3")
    rs.put(r3)

    assert rs.get_stats(0, 1e15) == {"#p3": 2 * 5 * 24 * 60 * 60 + 10}

    # Test doing queries within records
    assert len(rs.get_records("2018-04-22 00:00:00", "2018-04-23 00:00:00").keys()) == 1
    assert rs.get_stats("2018-04-22 00:00:00", "2018-04-23 00:00:00") == {
        "#p3": 24 * 60 * 60
    }
    assert len(rs.get_records("2018-04-23 00:00:00", "2018-04-24 00:00:00").keys()) == 2
    assert rs.get_stats("2018-04-23 00:00:00", "2018-04-24 00:00:00") == {
        "#p3": 2 * 24 * 60 * 60
    }
    assert len(rs.get_records("2018-04-23 00:00:00", "2018-04-24 00:00:01").keys()) == 3
    assert rs.get_stats("2018-04-23 00:00:00", "2018-04-24 00:00:01") == {
        "#p3": 2 * 24 * 60 * 60 + 3
    }
    assert rs.get_stats("2018-01-01 00:00:00", "2018-12-01 00:00:00") == {
        "#p3": 5 * 24 * 60 * 60 + 5 * 24 * 60 * 60 + 10
    }

    # Add records some time after
    r4 = rs.create("2018-05-02 08:00:00", "2018-05-02 10:00:00", "#p5")
    rs.put(r4)

    # Test some more queries
    assert len(rs.get_records("2018-01-01 00:00:00", "2018-12-31 00:00:00").keys()) == 4
    assert rs.get_stats("2018-01-01 00:00:00", "2018-12-01 00:00:00") == {
        "#p3": 5 * 24 * 60 * 60 + 5 * 24 * 60 * 60 + 10,
        "#p5": 2 * 60 * 60,
    }
    assert rs.get_stats("2018-05-01 00:00:00", "2018-05-02 00:00:00") == {}

    # Cleanup
    for record in rs.get_records(0, 1e15).values():
        rs.put(record.clone(ds="HIDDEN"))

    # Verify that all is gone
    assert len(rs._heap) == 1
    assert len(rs._heap[0].keys()) == 0
    assert len(rs._heap0_bin2record_keys.keys()) == 0
    # assert len(rs._items.keys()) == 0


def test_record_mutations():
    datastore = DataStoreStub()
    rs = RecordStore(datastore)

    # First pretend local mutations, rt == 0

    # Note that in these tests, we must set the mt of the records already
    # present in the store, because put() sets the mt.

    # Create a record
    r1 = rs.create("2018-04-20 10:00:00", "2018-04-20 11:00:00", "#p11")
    assert r1.mt > 0
    assert r1.st == 0
    rs.put(r1)
    assert rs.get_stats(0, 1e15) == {"#p11": 3600}

    # Now mutate it with older record - wont work
    r2 = r1.clone(ds="#p12")
    rs._items[r1.key].mt = r2.mt + 1
    rs.put(r2)
    assert rs.get_stats(0, 1e15) == {"#p11": 3600}

    # Now mutate it with same mt record - will work, since server time is zero.
    r2 = r1.clone(ds="#p12")
    rs._items[r1.key].mt = r2.mt
    rs.put(r2)
    assert rs.get_stats(0, 1e15) == {"#p12": 3600}

    # Now mutate it with newer mt record - will work
    r2 = r1.clone(mt=r1.mt + 1, ds="#p13")
    rs._items[r1.key].mt = r2.mt - 1
    rs.put(r2)
    assert rs.get_stats(0, 1e15) == {"#p13": 3600}

    # Now pretend mutations from the server. We can now set mt on the item.

    # Now mutate with older record - wont work
    r3 = r2.clone(rt=100, mt=r2.mt - 1, ds="#p14")
    assert r2.mt > r3.mt
    rs._put_received(r3)
    assert rs.get_stats(0, 1e15) == {"#p13": 3600}

    # Now mutate it with same mt record - will work, since server time is larger
    r3 = r2.clone(rt=100, mt=r2.mt, ds="#p14")
    assert r2.mt == r3.mt
    rs._put_received(r3)
    assert rs.get_stats(0, 1e15) == {"#p14": 3600}

    # Now mutate it with newer mt record - will work (even if rt is same)
    r3 = r2.clone(rt=100, mt=r2.mt + 2, ds="#p21")
    assert r2.mt < r3.mt
    rs._put_received(r3)
    assert rs.get_stats(0, 1e15) == {"#p21": 3600}

    # Now mutate it with newer mt record - will work (even if rt is less)
    r3 = r2.clone(rt=0, mt=r2.mt + 3, ds="#p22")
    assert r2.mt < r3.mt
    rs._put_received(r3)
    assert rs.get_stats(0, 1e15) == {"#p22": 3600}

    # Now drop it
    rs._drop(r3.key)
    assert rs.get_stats(0, 1e15) == {}


def test_invalid_records():
    datastore = DataStoreStub()
    rs = RecordStore(datastore)

    assert len(rs._items.keys()) == 0

    # Put one record in
    r = rs.create("2018-04-20 10:00:00", "2018-04-20 10:00:01", "#p1")
    rs.put(r)
    assert len(rs._items.keys()) == 1

    # Try putting more in - but all are missing a required field
    for key in ("key", "t1", "t2"):
        r = rs.create("2018-04-20 10:00:00", "2018-04-20 10:00:01", "#p1")
        r.pop(key)
        rs.put(r)
    assert len(rs._items.keys()) == 1

    # Try putting more in - but all have an invalid type in a field
    for key, val in dict(t1="x", t2="x").items():
        r = rs.create("2018-04-20 10:00:00", "2018-04-20 10:00:01", "#p1")
        r[key] = val
        rs.put(r)
    assert len(rs._items.keys()) == 1


def test_record_running():
    datastore = DataStoreStub()
    rs1 = RecordStore(datastore)

    # Add a one second record
    r1 = rs1.create("2018-04-20 10:00:00", "2018-04-20 10:00:01", "#p11")
    rs1.put(r1)

    assert rs1.get_stats(0, 1e15) == {"#p11": 1}
    assert len(rs1.get_records(0, 1e15)) == 1

    datastore = DataStoreStub()
    rs2 = RecordStore(datastore)

    # Add a zero-second record, i.e. a running  record
    r2 = rs2.create("2018-04-20 10:00:00", "2018-04-20 10:00:00", "#p11")
    rs2.put(r2)

    # The stats will indicate it as running until *now*
    assert rs2.get_running_records() == [r2]
    assert rs2.get_stats(0, 1e15)["#p11"] > 17756100
    assert len(rs2.get_records(0, 1e15)) == 1

    # Stop the record
    r2.t2 = r2.t1 + 10
    rs2.put(r2)

    assert rs2.get_running_records() == []
    assert rs2.get_stats(0, 1e15)["#p11"] == 10
    assert len(rs2.get_records(0, 1e15)) == 1


def test_deleting_records():
    datastore = DataStoreStub()
    rs = RecordStore(datastore)

    assert len(rs._items.keys()) == 0

    # Put one record in
    r = rs.create("2021-01-28 10:00:00", "2021-01-28 11:00:00", "#p1")
    rs.put(r)
    assert len(rs._items.keys()) == 1
    assert len(rs.get_records(0, 1e15)) == 1

    # Mark deleted
    make_hidden(r)
    assert r.ds == "HIDDEN #p1"
    make_hidden(r)
    assert r.ds == "HIDDEN #p1"

    # Update it
    rs.put(r)
    assert len(rs._items.keys()) == 1
    assert len(rs.get_records(0, 1e15)) == 0

    # And again (emulating coming back from the server, guards against issue #48)
    rs.put(r)
    assert len(rs._items.keys()) == 1
    assert len(rs.get_records(0, 1e15)) == 0

    # Revive it
    r.ds = "#p1"
    rs.put(r)
    assert len(rs._items.keys()) == 1
    assert len(rs.get_records(0, 1e15)) == 1

    # Put another record in
    r2 = rs.create("2021-01-28 11:00:00", "2021-01-28 12:00:00", "#p1")
    rs.put(r2)
    assert len(rs._items.keys()) == 2
    assert len(rs.get_records(0, 1e15)) == 2
    assert len(rs.get_stats(0, 1e15)) == 1  # because same project

    # Delete the record again, and push
    make_hidden(r)
    rs.put(r)
    assert len(rs._items.keys()) == 2
    assert len(rs.get_records(0, 1e15)) == 1
    assert len(rs.get_stats(0, 1e15)) == 1

    # Again (guards against issue #48)
    rs.put(r)
    assert len(rs._items.keys()) == 2
    assert len(rs.get_records(0, 1e15)) == 1
    assert len(rs.get_stats(0, 1e15)) == 1


if __name__ == "__main__":
    run_tests(globals())
