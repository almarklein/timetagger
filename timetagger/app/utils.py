"""
Utilities.
"""

from pscript import this_is_js
from pscript.stubs import (
    window,
    perf_counter,
    localStorage,
    RawJS,
    Math,
    JSON,
    undefined,
)


def looks_like_desktop():
    return window.screen.width >= 800


# From https://github.com/hsluv/hsluv/tree/master/javascript
# hue is a number between 0 and 360, saturation and lightness are numbers between 0 and 100.
# returns an array of 3 numbers between 0 and 1, for the r, g, and b channel.
def _get_hsluv2rgb():
    RawJS(
        """
    function f(a){var c=[],b=Math.pow(a+16,3)/1560896;b=b>g?b:a/k;for(var d=0;3>d;){var e=d++,h=l[e][0],w=l[e][1];e=l[e][2];for(var x=0;2>x;){var y=x++,z=(632260*e-126452*w)*b+126452*y;c.push({b:(284517*h-94839*e)*b/z,a:((838422*e+769860*w+731718*h)*a*b-769860*y*a)/z})}}return c}
    function m(a){a=f(a);for(var c=Infinity,b=0;b<a.length;){var d=a[b];++b;c=Math.min(c,Math.abs(d.a)/Math.sqrt(Math.pow(d.b,2)+1))}return c}
    function n(a,c){c=c/360*Math.PI*2;a=f(a);for(var b=Infinity,d=0;d<a.length;){var e=a[d];++d;e=e.a/(Math.sin(c)-e.b*Math.cos(c));0<=e&&(b=Math.min(b,e))}return b}
    function p(a,c){for(var b=0,d=0,e=a.length;d<e;){var h=d++;b+=a[h]*c[h]}return b}
    function q(a){return.0031308>=a?12.92*a:1.055*Math.pow(a,.4166666666666667)-.055}
    function t(a){return[q(p(l[0],a)),q(p(l[1],a)),q(p(l[2],a))]}
    function E(a){var c=a[0];if(0==c)return[0,0,0];var b=a[1]/(13*c)+C;a=a[2]/(13*c)+D;c=8>=c?B*c/k:B*Math.pow((c+16)/116,3);b=0-9*c*b/((b-4)*a-b*a);return[b,c,(9*c-15*a*c-a*b)/(3*a)]}
    function G(a){var c=a[1],b=a[2]/360*2*Math.PI;return[a[0],Math.cos(b)*c,Math.sin(b)*c]}
    function H(a){var c=a[0],b=a[1];a=a[2];if(99.9999999<a)return[100,0,c];if(1E-8>a)return[0,0,c];b=n(a,c)/100*b;return[a,b,c]}
    function J(a){var c=a[0],b=a[1];a=a[2];if(99.9999999<a)return[100,0,c];if(1E-8>a)return[0,0,c];b=m(a)/100*b;return[a,b,c]}
    function O(a){return t(E(G(a)))}
    function Q(a){return O(H(a))}
    function S(a){return O(J(a))}
    var l=[[3.240969941904521,-1.537383177570093,-.498610760293],[-.96924363628087,1.87596750150772,.041555057407175],[.055630079696993,-.20397695888897,1.056971514242878]],v=[[.41239079926595,.35758433938387,.18048078840183],[.21263900587151,.71516867876775,.072192315360733],[.019330818715591,.11919477979462,.95053215224966]],B=1,C=.19783000664283,D=.46831999493879,k=903.2962962,g=.0088564516,M="0123456789abcdef";

    // hsluvToRgb:Q, hpluvToRgb:S
    function hsluv2rgb(h, s, l) {return Q([h, s, l]);}
    """
    )
    return hsluv2rgb


if this_is_js():
    hsluv2rgb = _get_hsluv2rgb()


def fit_font_size(ctx, available_width, font, text, maxsize=100):
    """Fit a piece of text into a specified available space and return the size."""
    PSCRIPT_OVERLOAD = False  # noqa
    # Takes 2-5 iters, smaller available_width -> faster iteration
    size = maxsize
    width = available_width + 2
    while width > available_width and size > 4:
        new_size = int(1.1 * size * available_width / width)
        size = new_size if new_size < size else size - 1
        ctx.font = str(size) + "px " + font
        width = ctx.measureText(text).width
    return size


def rgba_from_hue(hue, alpha=1, lightness=0.7, saturation=0.75):
    """Generate a color based on the given hue."""
    PSCRIPT_OVERLOAD = False  # noqa
    # Classic HSV with color space
    # return f"hsla({hue},90%,{100*lightness:.0f}%,{alpha})"  # hue, saturation, lightness
    # HSLuv color space (https://en.wikipedia.org/wiki/HSLuv): constant lightness
    rgb = hsluv2rgb(hue, 100 * saturation, 100 * lightness)
    r, g, b = int(rgb[0] * 255.99), int(rgb[1] * 255.99), int(rgb[2] * 255.99)
    return "rgba(" + r + "," + g + "," + b + "," + alpha + ")"


def color_from_hue(hue, lightness=0.7, saturation=0.95):
    """Generate a color hex value for a given hue. Not used in the app,
    but convenient during dev.
    """
    rgb = hsluv2rgb(hue, 100 * saturation, 100 * lightness)
    r, g, b = int(rgb[0] * 255.99), int(rgb[1] * 255.99), int(rgb[2] * 255.99)
    m = "0123456789ABCDEF"
    return (
        "#" + m[r // 16] + m[r % 16] + m[g // 16] + m[g % 16] + m[b // 16] + m[b % 16]
    )


_lasthashedcolors = {}  # memorization for color_from_name()


def color_from_name(name):
    """Generate an arbitrary (but consistent) color from a palette,
    by hashing the given name.
    """
    PSCRIPT_OVERLOAD = False  # noqa
    if _lasthashedcolors[name] is window.undefined:
        color = len(name) * 271  # prime number
        for i in range(len(name)):
            color += name.charCodeAt(i) * 71
        _lasthashedcolors[name] = PALETTE1[color % len(PALETTE1)]
    return _lasthashedcolors[name]


def create_palettes():

    # The Github color palette, consisting of 8 strong colors and 8 lighter variants.
    # The difference between these variants is pretty big.
    # gh_colors = (
    #     "#B60205 #D93F0B #FBCA04 #0E8A16 #006B75 #1D76DB #0052CC #5319E7 "
    #     + "#E99695 #F9D0C4 #FEF2C0 #C2E0C6 #BFDADC #C5DEF5 #BFD4F2 #D4C5F9"
    # ).split(" ")
    # return gh_colors, gh_colors, 8

    # Generate a palette from the hsluv space. Avoid too bright values,
    # since it loses uniformity there. We chose a palette with uniform
    # saturation, varying lightness and hue only.
    n_hues = 10
    saturation = 0.75
    hsv_colors = []
    for lightness in (0.85, 0.70, 0.55, 0.40):
        for i in range(n_hues):
            hue = 360 * i / n_hues + 7  # Add a bit to obtain a nice red
            hex = color_from_hue(hue, lightness, saturation)
            hsv_colors.push(hex)
    # Done. Use only the middle two rows for auto-assigning colors.
    return hsv_colors[n_hues : 3 * n_hues], hsv_colors, n_hues


# Generate a palette for auto-assigning colors, and one for user colors
if this_is_js():
    PALETTE1, PALETTE2, PALETTE_COLS = create_palettes()


def is_valid_tag_charcode(cc):
    if (
        not (cc > 47 and cc < 58)
        and not (cc > 64 and cc < 91)  # numeric (0-9)
        and not (cc > 96 and cc < 123)  # upper alpha (A-Z)
        and not (cc == 45 or cc == 47 or cc == 95)  # lower alpha (a-z)
        and not (cc > 127)  # - / _  # non-ascii
    ):
        return False
    else:
        return True


def convert_text_to_valid_tag(s):
    """Convert any given text into a tag. If the tag name is less than 2 chars,
    returns an empty string.
    """
    tag_name = "#"
    last_char = "-"
    for i in range(len(s)):
        if is_valid_tag_charcode(ord(s[i])):
            c = s[i]
        else:
            c = "-"
            if last_char == "-":
                continue
        tag_name += c
        last_char = c

    if len(tag_name) < 3:
        tag_name = ""
    return tag_name


def get_tags_and_parts_from_string(s="", sorted=True):
    """Given a string, return a sorted list of tags, and a list of text parts
    that can be concatenated into the (nearly) original string.

    A bit of normalization is done as well:
    * the tags are made lowercase.
    * Leading and standalone # symbols are cleared.
    * Add a space between tags that are #glued#together.
    * Trim trailing whitespace.

    A valid tag starts with '#' followed by any alphanumerical characters,
    including dash, underscore, forward slash, and anything above 127.
    """

    parts = []
    tags = {}
    tag_start = -1
    tag_end = 0

    for i in range(len(s) + 1):
        cc = ord(s[i]) if i < len(s) else 35
        if tag_start < 0:
            if cc == 35:  # hash symbol (#)
                tag_start = i
                text = s[tag_end:i]
                if len(text) > 0:
                    if len(parts) > 0 and parts[-1][0] != "#":
                        parts[-1] = parts[-1] + text
                    else:
                        parts.append(text)
        else:
            if not is_valid_tag_charcode(cc):
                text = s[tag_start:i]
                if len(text) > 1:  # dont count the # symbol
                    tag = text.lower()
                    parts.append(tag)
                    tags[tag] = tag
                if cc == 35:
                    parts.append(" ")  # add a space #between#tags
                    tag_start = i
                else:
                    tag_start = -1
                    tag_end = i
    if len(parts) > 0:
        last = parts[-1].rstrip()
        if len(last) > 0:
            parts[-1] = last
        else:
            parts.pop(-1)
    tags = tags.values()
    if not this_is_js():
        tags = list(tags)
    if sorted:
        tags.sort()
    return tags, parts


def get_better_tag_order_from_stats(
    stats, selected_tags, remove_selected, priorities=None
):
    """Given a stats dict (tagz -> times) put the tags of each item in a
    sensible order. Returns a dict that maps the old tagz to the new.
    """
    PSCRIPT_OVERLOAD = False  # noqa

    # The task seems so simple, but doing this well is not trivial at all :)

    # Select tags (discart unselected)
    if len(selected_tags) > 0:
        ori_stats = stats
        stats = {}
        for tagz in ori_stats.keys():
            tags = tagz.split(" ")
            if all([tag in tags for tag in selected_tags]):
                stats[tagz] = ori_stats[tagz]

    # We have three scores, in increasing importance. Each applies to individual tags.
    depth = 0  # Used down below
    tag_scores1 = {}
    tag_scores2 = {}
    tag_scores3 = {}
    for tagz in stats.keys():
        tags = tagz.split(" ")
        depth = max(depth, len(tags))
        for tag in tags:
            tag_scores1[tag] = 0
            tag_scores2[tag] = 0
            tag_scores3[tag] = 0

    # Score 1: A score based on duration.
    for tagz, t in stats.items():
        for tag in tagz.split(" "):
            tag_scores1[tag] = tag_scores1.get(tag, 0) + t

    # Score 2: A score based on how often a tag occurs.
    # This works by letting each tag deal out points to other tags that
    # it occurs with together, which gives a nicer result than just
    # counting occurances.
    tag_connections = {}
    for tagz, t in stats.items():
        for tag in tagz.split(" "):
            tag_connections[tag] = tag_connections.get(tag, 0) + 1
    for tagz, t in stats.items():
        tags = tagz.split(" ")
        for tag in tags:
            for tag2 in tags:
                if tag2 != tag:
                    tag_scores2[tag2] += 1 / tag_connections[tag]

    # Score 3: A score based on priority and selection. Overrides the other scores.
    if priorities is not None:
        for tag in tag_scores3.keys():
            priority = priorities.get(tag, 0) or 1
            tag_scores3[tag] -= min(priority, 10)
    for i, tag in enumerate(selected_tags):
        d = 100 - i * 10
        tag_scores3[tag] = tag_scores3.get(tag, 0) + d

    # Sort the tagz (tag combis), based on the tag_scores.
    # This will be the order for the renaming process. This is important,
    # because the order of processing determines the way things are grouped.
    sorted_tagz = []
    for tagz in stats.keys():
        score1 = 0
        score2 = 0
        score3 = 0
        for tag in tagz.split(" "):
            score1 += tag_scores1[tag]
            score2 += tag_scores2[tag]
            score3 += tag_scores3[tag]
        sorted_tagz.append((tagz, score1, score2, score3))
    sorted_tagz.sort(key=lambda x: -x[1])
    sorted_tagz.sort(key=lambda x: -x[2])
    sorted_tagz.sort(key=lambda x: -x[3])

    # Rename the tagz (change tag order) based on the tag score
    name_map = {}
    position_votes = {}
    for tagz, _, _, _ in sorted_tagz:
        tags = tagz.split(" ")
        # Optionally clear the list from selected tags
        if remove_selected:
            for tag in selected_tags:
                if tag in tags:
                    tags.remove(tag)
        # Sort the tags, in a way that tries to preserve the structure of the
        # tags. This is done by remembering at what position each tag was present.
        remaining_tags = tags.copy()
        tags = []
        i = -1
        while len(remaining_tags) > 0:
            i += 1
            remaining_tags.sort(key=lambda tag: -tag_scores1[tag])
            remaining_tags.sort(key=lambda tag: -tag_scores2[tag])
            remaining_tags.sort(key=lambda tag: -tag_scores3[tag])
            remaining_tags.sort(key=lambda tag: -position_votes.get(str(i) + tag, 0))
            tags.append(remaining_tags.pop(0))
        name_map[tagz] = " ".join(tags)
        # Promote current position of each tag (and demote other positions)
        for i, tag in enumerate(tags):
            for ii in range(depth):
                pos_key = str(ii) + tag
                s = 1 if i == ii else -1 / depth
                position_votes[pos_key] = position_votes.get(pos_key, 0) + s

    return name_map


def order_stats_by_duration_and_name(items):
    """Given a list of "stat items", each a dict with (at least) fields "tagz"
    and "t", sort the items by duration (t), while grouping items with the
    same base tags.
    """
    PSCRIPT_OVERLOAD = False  # noqa

    # Calculate sub-scores
    sub_tagz_scores = {}
    for d in items:
        tags = d.tagz.split(" ")
        for i in range(len(tags)):
            tagz = tags[: i + 1].join(" ")
            sub_tagz_scores[tagz] = sub_tagz_scores.get(tagz, 0) + d.t

    def sortfunc(d1, d2):
        tags1 = d1.tagz.split(" ")
        tags2 = d2.tagz.split(" ")
        # Find the minimal truncated tagz that is different
        for i in range(max(len(tags1), len(tags2))):
            tagz1 = tags1[: i + 1].join(" ")
            tagz2 = tags2[: i + 1].join(" ")
            if tagz1 != tagz2:
                break
        # Sort based on the corresponding sub-score
        t1, t2 = sub_tagz_scores[tagz1], sub_tagz_scores[tagz2]
        if t1 < t2:
            return +1
        elif t1 > t2:
            return -1
        else:
            # Must be deterministic even in rare case of equal t
            # Note that tagz cannot be equal
            return -1 if (d1.tagz < d2.tagz) else +1

    # Sort - note the JS API, not Py
    items.sort(sortfunc)


def timestr2tuple(text):
    PSCRIPT_OVERLOAD = False  # noqa
    # Cases to support:
    # hh:mm:ss
    # hh mm ss
    # hh mm
    # xxh xxm xxs
    # hhmmss
    # hhmm

    # Determine format
    text = text.strip().lower()
    format = "24h"
    if len(text) >= 3 and text[-1] == "m":
        if text[-2] == "p":
            format = "pm"
            text = text[:-2].rstrip()
        elif text[-2] == "a":
            format = "am"
            text = text[:-2].rstrip()

    values = {"h": "0", "m": "0", "s": "0", "_": ""}
    nextmap = {"h": "m", "m": "s", "s": "_", "_": "_"}

    pending = ""
    next_natural_target = "h"
    parse_count = 0
    for c in text + " ":
        if c in " :;,hms":
            if pending:
                target = c if c in "hms" else next_natural_target
                next_natural_target = nextmap[target]
                values[target] = pending
                parse_count += 1
            pending = ""
        elif c in "0123456789":
            if pending is not None:
                pending += c
        else:
            pending = None

    if parse_count == 0:
        return None, None, None

    # Turn 1345 into 13:45
    if parse_count == 1 and not text[-1] in ":;,hms":
        if len(values["h"]) > 2:
            values["m"] = values["h"][2:]
            values["h"] = values["h"][:2]
        if len(values["m"]) > 2:
            values["s"] = values["m"][2:4]
            values["m"] = values["m"][:2]

    # Get numbers
    h, m, s = int(values["h"]), int(values["m"]), int(values["s"])

    # Handle am and pm notation
    if format == "am" and h == 12:
        h = 0
    elif format == "pm" and h < 12:
        h += 12

    # We could protect user from accidentally typing 100 hours or so.
    # But being able to write 62m and durations of 24h+ also matter. See #129.
    # return min(h, 23), min(m, 59), min(s, 59)
    return h, m, s


def positions_mean_and_std(positions):
    """Calculate the mean and std for a list of positions."""
    PSCRIPT_OVERLOAD = False  # noqa

    n = len(positions)
    avg_pos = [0, 0]
    for i in range(len(positions)):
        pos = positions[i]
        avg_pos[0] += pos[0] / n
        avg_pos[1] += pos[1] / n
    var_pos = [0, 0]
    for i in range(len(positions)):
        pos = positions[i]
        var_pos[0] += (pos[0] - avg_pos[0]) ** 2 / (n - 1)
        var_pos[1] += (pos[1] - avg_pos[1]) ** 2 / (n - 1)
    std_pos = var_pos[0] ** 0.5, var_pos[1] ** 0.5
    return avg_pos, std_pos


def get_pixel_ratio(ctx):
    """Get the ratio of logical pixel to screen pixel."""
    PSCRIPT_OVERLOAD = False  # noqa

    dpr = window.devicePixelRatio or 1
    bsr = (
        ctx.webkitBackingStorePixelRatio
        or ctx.mozBackingStorePixelRatio
        or ctx.msBackingStorePixelRatio
        or ctx.oBackingStorePixelRatio
        or ctx.backingStorePixelRatio
        or 1
    )
    return dpr / bsr


def create_pointer_event(node, e):
    # From flexx.ui.Widget
    # Get offset to fix positions
    rect = node.getBoundingClientRect()
    offset = rect.left, rect.top

    if e.type.startswith("touch"):
        # Touch event - select one touch to represent the main position
        t = e.changedTouches[0]
        pos = float(t.clientX - offset[0]), float(t.clientY - offset[1])
        page_pos = t.pageX, t.pageY
        button = 0
        buttons = []
        # Include basic support for multi-touch
        touches = {}
        for i in range(e.changedTouches.length):
            t = e.changedTouches[i]
            if t.target is not e.target:
                continue
            touches[t.identifier] = (
                float(t.clientX - offset[0]),
                float(t.clientY - offset[1]),
                t.force,
            )
        ntouches = e.touches.length
    else:
        # Mouse event
        pos = float(e.clientX - offset[0]), float(e.clientY - offset[1])
        page_pos = e.pageX, e.pageY
        # Fix buttons
        if e.buttons:
            buttons_mask = reversed([c for c in e.buttons.toString(2)]).join("")
        elif e.which:
            buttons_mask = [e.which.toString(2)]  # e.g. Safari (but also 1 for RMB)
        else:
            # libjavascriptcoregtk-3.0-0  version 2.4.11-1 does not define
            # e.buttons
            buttons_mask = [e.button.toString(2)]
        buttons = [i + 1 for i in range(5) if buttons_mask[i] == "1"]
        button = {0: 1, 1: 3, 2: 2, 3: 4, 4: 5}[e.button]
        touches = {-1: (pos[0], pos[1], 1)}  # key must not clash with real touches
        ntouches = buttons.length

    # note: our button has a value as in JS "which"
    modifiers = [n for n in ("Alt", "Shift", "Ctrl", "Meta") if e[n.lower() + "Key"]]
    # Create event dict
    return dict(
        pos=pos,
        page_pos=page_pos,
        touches=touches,
        ntouches=ntouches,
        button=button,
        buttons=buttons,
        modifiers=modifiers,
    )


class RoundedPath:
    """A helper class to create a closed path with rounded corners."""

    def __init__(self):
        self._points = []

    def addVertex(self, x, y, r):
        self._points.push((x, y, r))

    def toPath2D(self):
        PSCRIPT_OVERLOAD = False  # noqa

        path = window.Path2D()

        points = self._points.copy()
        points.insert(0, self._points[-1])
        points.append(self._points[0])

        for i in range(len(self._points)):
            x1, y1, r1 = points[i]
            x2, y2, r2 = points[i + 1]  # its about this point
            x3, y3, r3 = points[i + 2]

            dx1, dy1 = x1 - x2, y1 - y2
            dx3, dy3 = x3 - x2, y3 - y2
            dn1 = (dx1 * dx1 + dy1 * dy1) ** 0.5
            dn3 = (dx3 * dx3 + dy3 * dy3) ** 0.5
            dn1 = max(dn1, 0.001)
            dn3 = max(dn3, 0.001)

            r = min(min(dn1 / 3, dn3 / 3), r2)
            x1, y1 = x2 + r * dx1 / dn1, y2 + r * dy1 / dn1
            x3, y3 = x2 + r * dx3 / dn3, y2 + r * dy3 / dn3

            n_segments = max(int(0.5 * r), 1)
            for j in range(n_segments + 1):
                f3 = j / n_segments
                f1 = 1 - f3
                f2 = min(f1, f3)
                x = (f1 * x1 + f2 * x2 + f3 * x3) / (f1 + f2 + f3)
                y = (f1 * y1 + f2 * y2 + f3 * y3) / (f1 + f2 + f3)
                path.lineTo(x, y)

        path.closePath()
        return path


class Picker:
    """A class that helps with picking."""

    def __init__(self):
        self.clear()

    def clear(self):
        """Call this at the start of a draw."""
        self._regions = []

    def register(self, x1, y1, x2, y2, pick_object):
        """Register a clickable region for the given object.
        Use this during drawing.
        """
        self._regions.insert(0, (x1, y1, x2, y2, pick_object))

    def pick(self, x, y):
        """Get pick object for the given location. Returns None if nothing
        was picked.
        """
        for x1, y1, x2, y2, ob in self._regions:
            if y1 < y < y2 and x1 < x < x2:
                return ob


class SimpleSettings:
    """Base API for storing settings. The "simple" refers to the API.
    Key-value pairs are stored in a cache for fast getters.
    The actual storage can be:
    * None / session only: unknown keys are not stored across sessions.
    * Local storagee: a prefefined set of keys are stored in local storaged,
      which means that they are device-specific.
    * Synced: synced to the server using the settings store.
    """

    def __init__(self):
        # Define the settings and the defaults
        self._local_keys = {
            "darkmode": 1,
            "width_mode": "auto",
            "pomodoro_enabled": False,
            "report_grouping": "date",
            "report_hidesecondary": False,
            "report_hourdecimals": False,
            "report_showrecords": True,
        }
        self._synced_keys = {
            "first_day_of_week": 1,
            "time_repr": "auto",
            "duration_repr": "hms",
            "today_snap_offset": "",
            "show_stopwatch": True,
        }
        # The data store for synced source
        self._store = None
        # Init
        self._cache = {}
        self._load_local()
        self._load_synced()  # wont do anything except init the cache
        self._flush_local()
        self._flush_synced()

    def update_store(self, store):
        """Called by the root store."""
        self._store = store
        self._load_synced()
        self._flush_synced()

    def _flush_local(self):
        # Load default, then try loading from other source (in case we switched the source)
        # and then load from the proper source.
        for key in self._local_keys.keys():
            value = self._local_keys[key]
            value = self._synced_cache.get(key, value)
            value = self._local_cache.get(key, value)
            self._cache[key] = value

    def _flush_synced(self):
        for key in self._synced_keys.keys():
            value = self._synced_keys[key]
            value = self._local_cache.get(key, value)
            value = self._synced_cache.get(key, value)
            self._cache[key] = value

    def _load_local(self):
        self._local_cache = {}
        x = localStorage.getItem("timetagger_local_settings")
        if x:
            try:
                self._local_cache = JSON.parse(x)
            except Exception as err:
                window.console.warn("Cannot parse local settings JSON: " + str(err))

    def _save_local(self, key):
        x = JSON.stringify(self._local_cache)
        localStorage.setItem("timetagger_local_settings", x)

    def _load_synced(self):
        self._synced_cache = {}
        if self._store:
            for key in self._synced_keys.keys():
                ob = self._store.get_by_key(key)
                if ob is not None:
                    self._synced_cache[key] = ob.value

    def _save_synced(self, key):
        if self._store:
            value = self._synced_cache.get(key, self._synced_keys[key])
            ob = self._store.create(key, value)
            self._store.put(ob)

    def get(self, key, default_=None):
        """Get a settings item."""
        value = self._cache[key]
        return default_ if value is undefined else value

    def set(self, key, value):
        """Save a setting."""
        self._cache[key] = value
        # Save
        if key in self._local_keys.keys():
            self._local_cache[key] = value
            self._save_local(key)
        elif key in self._synced_keys.keys():
            self._synced_cache[key] = value
            self._save_synced(key)


if this_is_js():
    window.simplesettings = SimpleSettings()


class BaseCanvas:
    """A Canvas wrapper that automatically resizes and takes high-res into account."""

    def __init__(self, node):
        self.node = node
        self.node.js = self
        self.w = 0
        self.h = 0
        self._pending_draw = False
        self._mouse_tracking = False
        self._init_events()
        self.has_mouse = False
        self.node.setAttribute("tabindex", -1)  # allow catching key events

        # For tooltips
        self._pointer_hover = ""
        self._tooltips = Picker()
        self._tooltipdiv = window.document.createElement("div")
        self._tooltipdiv.className = "tooltipdiv"
        self._tooltipdiv.rect = None
        self.node.parentNode.appendChild(self._tooltipdiv)

        # Do draws on a regular interval
        self._draw_tick()

    def _init_events(self):

        # Disable context menu so we can handle RMB clicks
        # Firefox is particularly stuborn with Shift+RMB, and RMB dbl click
        for ev_name in ("contextmenu", "click", "dblclick"):
            window.document.addEventListener(ev_name, self._prevent_default_event, 0)

        # Keep track of wheel event directed at the canvas
        self.node.addEventListener("wheel", self._on_js_wheel_event, 0)

        # If the canvas uses the wheel event for something, you'd want to
        # disable browser-scroll when the mouse is over the canvas. But
        # when you scroll down a page and the cursor comes over the canvas
        # because of that, we don't want the canvas to capture too eagerly.
        # This code only captures if there has not been scrolled elsewhere
        # for about half a second.
        if not window._wheel_timestamp:
            window._wheel_timestamp = 0, ""
            window.document.addEventListener("wheel", self._on_js_wheel_global, 0)

        # Keep track of mouse events
        self.node.addEventListener("mousedown", self._on_js_mouse_event, 0)
        window.document.addEventListener("mouseup", self._on_js_mouse_event, 0)
        window.document.addEventListener("mousemove", self._on_js_mouse_event, 0)

        window.document.addEventListener("mousemove", self._tooltip_handler, 0)
        self.node.addEventListener("mousedown", self._tooltip_handler, 0)
        self.node.addEventListener("touchstart", self._tooltip_handler, 0)
        self.node.addEventListener("touchmove", self._tooltip_handler, 0)
        self.node.addEventListener("touchend", self._tooltip_handler, 0)
        self.node.addEventListener("touchcancel", self._tooltip_handler, 0)

        # Keep track of touch events
        self.node.addEventListener("touchstart", self._on_js_touch_event, 0)
        self.node.addEventListener("touchend", self._on_js_touch_event, 0)
        self.node.addEventListener("touchcancel", self._on_js_touch_event, 0)
        self.node.addEventListener("touchmove", self._on_js_touch_event, 0)

        # Keep track of window size
        window.addEventListener("resize", self._on_js_resize_event, False)
        window.setTimeout(self._on_js_resize_event, 10)

    def _prevent_default_event(self, e):
        """Prevent the default action of an event unless all modifier
        keys (shift, ctrl, alt) are pressed down.
        """
        if e.target is self.node:
            # if not (e.altKey is True and e.ctrlKey is True and e.shiftKey is True):
            if not e.ctrlKey:
                e.preventDefault()

    def _on_js_wheel_global(self, e):
        id, t0 = window._wheel_timestamp
        t1 = perf_counter()
        if (t1 - t0) < 0.5:
            window._wheel_timestamp = id, t1  # keep scrolling
        else:
            window._wheel_timestamp = e.target.id, t1  # new scroll

    def _on_js_wheel_event(self, e):
        if e.ctrlKey:
            return
        if window._wheel_timestamp[0] == self.node.id:
            ev = create_pointer_event(self.node, e)
            ev.type = e.type
            ev.button = 0
            ev.hscroll = e.deltaX * [1, 16, 600][e.deltaMode]
            ev.vscroll = e.deltaY * [1, 16, 600][e.deltaMode]
            handled = self.on_wheel(ev)
            if handled:
                e.preventDefault()
                e.stopPropagation()

    def _on_js_mouse_event(self, e):
        if e.type == "mousedown":
            self._mouse_tracking = True
            self.node.focus()
        elif not self._mouse_tracking:
            return
        elif e.type == "mouseup":
            self._mouse_tracking = False

        e.preventDefault()
        ev = create_pointer_event(self.node, e)
        ev.type = "mouse_" + e.type[5:]
        if ev.type == "mouse_move" and len(ev.buttons) == 0:
            return  # cancel
        self.has_mouse = True
        self.on_pointer(ev)

    def _on_js_touch_event(self, e):
        e.preventDefault()
        ev = create_pointer_event(self.node, e)
        ev.type = "touch_" + {
            "start": "down",
            "move": "move",
            "end": "up",
            "cancel": "up",
        }.get(e.type[5:])
        self.on_pointer(ev)

    def _on_js_resize_event(self):
        """Ensure that the canvas has the correct size and dpi."""
        ctx = self.node.getContext("2d")
        self.pixel_ratio = get_pixel_ratio(ctx)

        # A line-width of 2 is great to have crisp images. For uneven line widths
        # one needs to offset 0.5 * pixel_ratio. But, that line-width must be
        # snapped to a width matching the pixel_ratio! pfew!
        self.grid_linewidth2 = min(self.pixel_ratio, self.grid_round(1)) * 2

        self.w, self.h = self.node.clientWidth, self.node.clientHeight
        self.node.width = self.w * self.pixel_ratio
        self.node.height = self.h * self.pixel_ratio
        self.update()
        self.on_resize(True)  # draw asap to avoid flicker

    def grid_round(self, x):
        """Round a value to the screen pixel grid."""
        PSCRIPT_OVERLOAD = False  # noqa
        return Math.round(x * self.pixel_ratio) / self.pixel_ratio

    def _draw_tick(self):
        """Function that calls update() to schedule a draw() on a regular interval.
        Where regular is really regular, so that second-ticks don't "jump".
        This functon must *not* be called more than once.
        """
        now = window.Date().getTime()
        res = 1000  # 1 FPS
        etime = int(now / res) * res + res
        window.setTimeout(self._draw_tick, etime - now)
        self.update()

    def update(self, asap=True):
        """Schedule an update."""
        # The extra setTimeout is to make sure that there is time for the
        # browser to process events (like scrolling).
        if not self._pending_draw:
            self._pending_draw = True
            if asap:
                window.requestAnimationFrame(self._draw)
            else:
                window.setTimeout(window.requestAnimationFrame, 10, self._draw)

    def _draw(self):
        """The entry draw function, called by the browser."""
        self._pending_draw = False
        if self.node.style.display == "none":
            return  # Hidden
        elif self.w <= 0 or self.h <= 0:
            return  # Probably still initializing

        ctx = self.node.getContext("2d")

        # Prepare hidpi mode for canvas  (flush state just in case)
        for i in range(4):
            ctx.restore()
        ctx.save()
        ctx.scale(self.pixel_ratio, self.pixel_ratio)

        self._tooltips.clear()

        # Draw
        self.on_draw(ctx)

    def _tooltip_handler(self, e):
        ev = create_pointer_event(self.node, e)
        x, y = ev.pos
        # Only on mouse - it's anoying for touch
        is_mouse = bool(ev.touches["-1"])
        if not is_mouse:
            self._tooltipdiv.style.display = "none"
            return
        # Get tooltip object - if text is None it means no tooltip
        ob = self._tooltips.pick(x, y)
        # Handle over. Schedule a new draw if the over-status changes.
        hash = "" if ob is None else ob.hash
        if hash != self._pointer_hover:
            self._pointer_hover = hash
            self.update()
        # Don't show a tooltip if its text is empty
        if ob is not None and not ob.text:
            ob = None
        # Handle touch events - show tt during a touch, but only after a delay
        delay = 400
        if e.type == "touchstart":
            delay = 200
        elif e.type == "touchend" or e.type == "touchcancel" or e.type == "touchmove":
            ob = None
        # Update our tooltip div
        if ob is not None:
            if e.type == "mousedown":  # down -> hide while we're over it
                self._tooltipdiv.style.display = "none"
            elif self._mouse_tracking:  # dont show tooltips while dragging
                pass
            elif self._tooltipdiv.rect != ob.rect:  # note: deep comparison
                # Prepare for showing tooltip, then show after a delay
                self._tooltipdiv.rect = ob.rect
                self._tooltipdiv.innerText = ob.text
                self._tooltipdiv.style.display = "block"
                self._tooltipdiv.style.transition = "none"
                self._tooltipdiv.style.opacity = 0
                if ob.positioning == "mouse":
                    self._tooltipdiv.ypos = y - 20
                elif ob.positioning == "below":
                    self._tooltipdiv.ypos = ob.rect[3]
                else:  # ob.positioning == "ob"
                    self._tooltipdiv.ypos = ob.rect[1]
                self._tooltipdiv.style.top = self._tooltipdiv.ypos + "px"
                if x < self.w - 200:
                    if ob.positioning == "below":
                        self._tooltipdiv.xpos = ob.rect[0] - 10
                    else:
                        self._tooltipdiv.xpos = ob.rect[2]
                    self._tooltipdiv.style.left = self._tooltipdiv.xpos + "px"
                    self._tooltipdiv.style.right = None
                else:
                    if ob.positioning == "below":
                        self._tooltipdiv.xpos = self.w - ob.rect[2] - 10
                    else:
                        self._tooltipdiv.xpos = self.w - ob.rect[0]
                    self._tooltipdiv.style.left = None
                    self._tooltipdiv.style.right = self._tooltipdiv.xpos + "px"
                window.setTimeout(self._tooltip_show, delay)
        elif self._tooltipdiv.rect is not None:
            # Hide tooltip, really un-display the div after a delay
            self._tooltipdiv.style.opacity = 0
            if self._tooltipdiv.style.left:
                self._tooltipdiv.style.left = self._tooltipdiv.rect[2] + "px"
            else:
                self._tooltipdiv.style.right = self.w - self._tooltipdiv.rect[0] + "px"
            self._tooltipdiv.rect = None
            window.setTimeout(self._tooltip_hide, 300)

    def _tooltip_hide(self):
        if self._tooltipdiv.rect is None:
            self._tooltipdiv.style.display = "none"
            self._tooltipdiv.style.left = None
            self._tooltipdiv.style.right = None

    def _tooltip_show(self):
        if self._tooltipdiv.rect is not None:
            self._tooltipdiv.style.transition = None
            self._tooltipdiv.style.opacity = 1
            self._tooltipdiv.style.top = self._tooltipdiv.ypos + "px"
            if self._tooltipdiv.style.left:
                self._tooltipdiv.style.left = self._tooltipdiv.xpos + 10 + "px"
            else:
                self._tooltipdiv.style.right = self._tooltipdiv.xpos + 10 + "px"

    def register_tooltip(self, x1, y1, x2, y2, text, positioning="ob"):
        """Register a tooltip at the given position.
        Returns whether the mouse hovers here now.
        """
        rect = [x1, y1, x2, y2]
        hash = str([int(x1), int(y1), int(x2), int(y2)])
        ob = {"rect": rect, "text": text, "positioning": positioning, "hash": hash}
        self._tooltips.register(x1, y1, x2, y2, ob)
        return self._pointer_hover == ob.hash

    # To overload

    def on_resize(self):
        pass

    def on_draw(self, ctx):
        pass

    def on_wheel(self, ev):
        pass

    def on_pointer(self, ev):
        pass


if __name__ == "__main__":
    import pscript

    pscript.script2js(
        __file__, target=__file__[:-3] + ".js", namespace="utils", module_type="simple"
    )
