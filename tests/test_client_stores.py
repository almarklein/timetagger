"""
Test other stores.
"""

import datetime

from _common import run_tests
from timetagger.app import stores


class Stub:
    def addEventListener(self, *args):
        pass

    def setTimeout(self, *args):
        pass

    def clearTimeout(self, *args):
        pass


stores.window = Stub()
stores.window.document = Stub()


def test_demo_record_store():
    ds = stores.DemoDataStore()

    # There are now records for only one year
    # Note that this test fails early januari :P
    if datetime.date.today().month > 1:
        assert len(ds.records.get_records(0, 1e15)) > 25
    assert len(ds.records.get_records(0, 1e15)) < 2000

    # Build other years
    for year in ds._years:
        ds._create_one_year_of_data(year)

    # Now we have the full demo. The demo generates the records async
    assert len(ds.records.get_records(0, 1e15)) > 2000

    stats = ds.records.get_stats(0, 1e15)
    assert len(stats.keys()) > 1
    print(stats)


if __name__ == "__main__":
    run_tests(globals())
