"""
Test some logic from the utils module.
Some of this is implicitly covered by the other tests, but not all.
"""


from _common import run_tests
from timetagger.client.utils import (
    convert_text_to_valid_tag,
    get_tags_and_parts_from_string,
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


if __name__ == "__main__":
    run_tests(globals())
