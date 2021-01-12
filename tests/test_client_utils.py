"""
Test some logic from the utils module.
Some of this is implicitly covered by the other tests, but not all.
"""


from _common import run_tests
from timetagger.client.utils import (
    convert_text_to_valid_tag,
    get_tags_and_parts_from_string,
    get_better_tag_order_from_stats,
)


def test_convert_text_to_valid_tag():

    # this function does not lowercase
    assert convert_text_to_valid_tag("#hi") == "#hi"
    assert convert_text_to_valid_tag("#HI") == "#HI"

    # Allowed: numeric, unicode, underscore, dashes, forward slashes
    assert convert_text_to_valid_tag("#1337") == "#1337"
    assert convert_text_to_valid_tag("#hë") == "#hë"
    assert convert_text_to_valid_tag("#h_a") == "#h_a"
    assert convert_text_to_valid_tag("#h-a") == "#h-a"
    assert convert_text_to_valid_tag("#h/a") == "#h/a"

    # Not allowed is converted to dashes
    assert convert_text_to_valid_tag("#h a") == "#h-a"
    assert convert_text_to_valid_tag("#h(a") == "#h-a"
    assert convert_text_to_valid_tag("#h)a") == "#h-a"
    assert convert_text_to_valid_tag("#h()[]\\|a") == "#h-a"

    # Converts names to actual tags
    assert convert_text_to_valid_tag("hi") == "#hi"
    assert convert_text_to_valid_tag("[a]") == "#a-"

    # Cannot be too short
    assert convert_text_to_valid_tag("") == ""
    assert convert_text_to_valid_tag("#") == ""
    assert convert_text_to_valid_tag("#a") == ""
    assert convert_text_to_valid_tag("a") == ""
    assert convert_text_to_valid_tag("#aa") == "#aa"
    assert convert_text_to_valid_tag("aa") == "#aa"
    assert convert_text_to_valid_tag("#]]]]]") == ""


def test_get_tags_and_parts_from_string():

    f = get_tags_and_parts_from_string

    # It gets sorted tags, and parts
    assert f("hey #aa and #bb")[0] == ["#aa", "#bb"]
    assert f("hey #bb and #aa")[0] == ["#aa", "#bb"]
    assert f("hey #aa and #bb")[1] == ["hey ", "#aa", " and ", "#bb"]

    # This function does lowercase
    assert f("hey #AA and #BB")[0] == ["#aa", "#bb"]
    assert f("hey #AA and #BB")[1] == ["hey ", "#aa", " and ", "#bb"]

    # It untangles tags too
    assert f("hey ##aa")[0] == ["#aa"]
    assert f("hey ##aa")[1] == ["hey ", " ", "#aa"]  # not perfect but good enough
    assert f("hey #aa#")[0] == ["#aa"]
    assert f("hey #aa#")[1] == ["hey ", "#aa", " "]
    assert f("hey #aa#bb")[0] == ["#aa", "#bb"]
    assert f("hey #aa#bb")[1] == ["hey ", "#aa", " ", "#bb"]

    # And removes trailing whitespace
    assert f("hey #aa #bb   ")[1] == ["hey ", "#aa", " ", "#bb"]

    # Test invalid chars too
    assert f("hey #foo\\bar and #spam*eggs")[0] == ["#foo", "#spam"]
    assert f("hey #foo\\bar and #spam*eggs")[1] == [
        "hey ",
        "#foo",
        "\\bar and ",
        "#spam",
        "*eggs",
    ]


def test_get_better_tag_order_from_stats():
    def get_better_tag_order(*args):
        return list(get_better_tag_order_from_stats(*args).values())

    # Some sanity checks
    assert get_better_tag_order({}, [], False) == []
    assert get_better_tag_order({"#foo #bar": 1}, [], False) == ["#foo #bar"]
    assert get_better_tag_order({"#bar #foo": 1}, [], False) == ["#bar #foo"]
    assert get_better_tag_order({"#foo #bar": 1}, ["#foo"], False) == ["#foo #bar"]
    assert get_better_tag_order({"#bar #foo": 1}, ["#foo"], False) == ["#foo #bar"]
    assert get_better_tag_order({"#foo #bar": 1}, ["#bar"], False) == ["#bar #foo"]
    assert get_better_tag_order({"#bar #foo": 1}, ["#bar"], False) == ["#bar #foo"]
    assert get_better_tag_order({"#bar #foo": 1}, ["#foo"], True) == ["#bar"]
    assert get_better_tag_order({"#bar #foo": 1}, ["#spam"], False) == []

    # A simple example
    stats = {"#aa #bb": 2, "#cc #aa": 4}

    stats2 = get_better_tag_order(stats, [], False)
    assert stats2 == ["#aa #cc", "#aa #bb"]

    stats2 = get_better_tag_order(stats, ["#aa"], False)
    assert stats2 == ["#aa #cc", "#aa #bb"]

    stats2 = get_better_tag_order(stats, ["#bb"], False)
    assert stats2 == ["#bb #aa"]

    stats2 = get_better_tag_order(stats, ["#cc"], False)
    assert stats2 == ["#cc #aa"]

    stats2 = get_better_tag_order(stats, ["#aa"], True)
    assert stats2 == ["#cc", "#bb"]

    stats2 = get_better_tag_order(stats, ["#cc"], True)
    assert stats2 == ["#aa"]

    # Semantic grouping
    stats = {
        "#code #client1": 2,
        "#meeting #client1": 4,
        "#code #client2": 2,
        "#admin #client2": 1,
    }
    stats2 = get_better_tag_order(stats, [], False)
    assert stats2 == [
        "#client1 #code",
        "#client2 #code",
        "#client1 #meeting",
        "#client2 #admin",
    ]
    stats2 = get_better_tag_order(stats, ["#code"], False)
    assert stats2 == ["#code #client1", "#code #client2"]

    # Semantic grouping (with prefix)
    stats = {
        "#paid #code #client1": 2,
        "#paid #meeting #client1": 4,
        "#paid #code #client2": 2,
        "#paid #admin #client2": 1,
    }
    stats2 = get_better_tag_order(stats, [], False)
    assert stats2 == [
        "#paid #client1 #code",
        "#paid #client2 #code",
        "#paid #client1 #meeting",
        "#paid #client2 #admin",
    ]
    stats2 = get_better_tag_order(stats, ["#paid"], True)
    assert stats2 == [
        "#client1 #code",
        "#client2 #code",
        "#client1 #meeting",
        "#client2 #admin",
    ]

    # Semantic grouping, take 2, from the demo (at some point)
    stats = {
        "#client1 #code": 5280,
        "#client1 #design": 4680,
        "#client3 #code": 5820,
        "#client3 #meeting": 3120,
        "#reading #unpaid": 2880,
    }
    stats2 = get_better_tag_order(stats, [], False)
    assert stats2 == [
        "#client1 #code",
        "#client3 #code",
        "#client1 #design",
        "#client3 #meeting",
        "#reading #unpaid",
    ]
    stats2 = get_better_tag_order(stats, ["#code"], False)
    assert stats2 == ["#code #client3", "#code #client1"]
    stats2 = get_better_tag_order(stats, ["#code"], True)
    assert stats2 == ["#client3", "#client1"]

    # Semantic grouping, take 3
    stats = {
        "#client1 #code": 5280,
        "#client1 #design": 4680,
        "#client1 #admin": 10,
        "#client3 #code": 5820,
    }
    stats2 = get_better_tag_order(stats, [], False)
    assert stats2 == [
        "#client1 #code",
        "#client1 #design",
        "#client1 #admin",
        "#client3 #code",
    ]


if __name__ == "__main__":
    run_tests(globals())
