"""
Utilities.
"""

from pscript import this_is_js
from pscript.stubs import window, perf_counter, RawJS, Math


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


_lasthashedhue = "", 0  # memorization for hue_from_name()


def hue_from_name(name):
    name = name.lower()
    PSCRIPT_OVERLOAD = False  # noqa

    if _lasthashedhue[0] != name:
        # todo: can we do something about subnames?
        subnames = [name]
        color = 0
        for level in range(len(subnames)):
            subname = subnames[level]
            # Get color of this subname, using a hash on all characters
            subcolor = len(subname) * 71  # prime number
            for i in range(len(subname)):
                subcolor += subname.charCodeAt(i) * 71
            # Add contribution to global color. The contribution varies less as
            # the sub-level increases (a quarter of the previous)
            maxcolor = 360 / 4 ** level
            subcolor = (subcolor % maxcolor) - maxcolor / 2
            subcolor = RawJS(
                "(subcolor < 0) ? (subcolor * 0.8 - 0.1*maxcolor) : (subcolor * 0.8 + 0.1*maxcolor)"
            )
            color += subcolor
        # Sign-safe modulo, just in case a browser has trouble with negative angles
        while color < 0:
            color += 360
        _lasthashedhue[0] = name
        _lasthashedhue[1] = color
    return _lasthashedhue[1]


def color_from_hue(hue, alpha=1, lightness=0.7, saturation=0.75):
    """Generate a color based on the given hue."""
    PSCRIPT_OVERLOAD = False  # noqa
    # Classic HSV with color space
    # return f"hsla({hue},90%,{100*lightness:.0f}%,{alpha})"  # hue, saturation, lightness
    # HSLuv color space (https://en.wikipedia.org/wiki/HSLuv): constant lightness
    rgb = hsluv2rgb(hue, 100 * saturation, 100 * lightness)
    r, g, b = int(rgb[0] * 255.99), int(rgb[1] * 255.99), int(rgb[2] * 255.99)
    return "rgba(" + r + "," + g + "," + b + "," + alpha + ")"


def hex_from_hue(hue, lightness=0.7, saturation=0.95):
    """Generate a color hex value for a given hue. Not used in the app,
    but convenient during dev.
    """
    rgb = hsluv2rgb(hue, 100 * saturation, 100 * lightness)
    r, g, b = int(rgb[0] * 255.99), int(rgb[1] * 255.99), int(rgb[2] * 255.99)
    m = "0123456789ABCDEF"
    return (
        "#" + m[r // 16] + m[r % 16] + m[g // 16] + m[g % 16] + m[b // 16] + m[b % 16]
    )


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


def get_tags_and_parts_from_string(s=""):
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
    tags.sort()
    return tags, parts


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


def make_context_sketchy(ctx):
    """Monkeypatch the context to make it draw sketchy lines and rects."""
    if not ctx._ori_moveTo:
        ctx._ori_moveTo = ctx.moveTo
        ctx._ori_lineTo = ctx.lineTo
        ctx._ori_save = ctx.save

    sf = 1.1  # noqa - sketch factor (1 means max 0.5 deviation)
    x0, y0 = 0, 0

    # Reproducable random numbers. Reproducable as in per-draw, but also
    # in between sessions with same data.
    # fmt: off
    random_numbers = [
        "0.6864", "0.5246", "0.9662", "0.0383", "0.4372", "0.9839",
        "0.7125", "0.6176", "0.2168", "0.7509", "0.0421", "0.2139",
        "0.2523", "0.0405", "0.1295", "0.5129", "0.7558", "0.8359",
        "0.0608", "0.0312", "0.6027", "0.0477", "0.2813", "0.4590",
        "0.3101", "0.1960", "0.2398", "0.6336", "0.8915", "0.3562",
        "0.3547", "0.1306", "0.6243", "0.2477", "0.5941", "0.5062",
        "0.4328", "0.9814", "0.7330", "0.9415", "0.7504", "0.3423",
        "0.8648", "0.2390", "0.4278", "0.8097", "0.2248", "0.3141",
        "0.0949", "0.5548", "0.8897", "0.8784", "0.3927", "0.0059",
        "0.3573", "0.6784", "0.3396", "0.6834", "0.4273", "0.0958",
        "0.9172", "0.6826", "0.2923", "0.8015",
    ]
    # fmt: on

    random_index = 0

    def random():
        nonlocal random_index
        random_index = RawJS("(random_index + 1) % random_numbers.length")
        return random_numbers[random_index]

    def save():
        nonlocal random_index
        random_index = 0
        ctx._ori_save()

    def moveTo(x, y, straight):
        nonlocal x0, y0
        RawJS(
            """
        if (straight) { return ctx._ori_moveTo(x, y); }
        ctx._ori_moveTo(x + sf * (random() - 0.5),
                            y + sf * (random() - 0.5));
        """
        )
        x0, y0 = x, y

    def lineTo(x, y, straight):
        nonlocal x0, y0
        RawJS(
            """
        if (straight) { return ctx._ori_lineTo(x, y); }
        var d = Math.sqrt(Math.pow(x-x0, 2) + Math.pow(y-y0,2));
        var n = Math.max(1, Math.ceil(d/25));
        for (var i=1; i<=n; i++) {
            var f = i/n;
            var x1 = (1-f) * x0 + f * x;
            var y1 = (1-f) * y0 + f * y;
            ctx._ori_lineTo(x1 + sf * (random() - 0.5),
                            y1 + sf * (random() - 0.5));
        }
        """
        )
        x0, y0 = x, y

    def strokeRect(x, y, w, h):
        PSCRIPT_OVERLOAD = False  # noqa
        ctx.beginPath()
        ctx.moveTo(x, y)
        ctx.lineTo(x + w, y)
        ctx.lineTo(x + w, y + h)
        ctx.lineTo(x, y + h)
        ctx.lineTo(x, y)
        ctx.stroke()

    def fillRect(x, y, w, h):
        PSCRIPT_OVERLOAD = False  # noqa
        ctx.beginPath()
        ctx.moveTo(x, y)
        ctx.lineTo(x + w, y)
        ctx.lineTo(x + w, y + h)
        ctx.lineTo(x, y + h)
        ctx.lineTo(x, y)
        ctx.fill()

    ctx.moveTo = moveTo
    ctx.lineTo = lineTo
    ctx.strokeRect = strokeRect
    ctx.fillRect = fillRect
    ctx.save = save


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


class BaseCanvas:
    """A Canvas wrapper that automatically resizes and takes high-res into account."""

    _SKETCHY = False

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
        self._tooltips = Picker()
        self._tooltipdiv = window.document.createElement("div")
        self._tooltipdiv.className = "tooltipdiv"
        self._tooltipdiv.rect = None
        self.node.parentNode.appendChild(self._tooltipdiv)

        # Do draws on a regular interval
        self._draw_tick()

        # Sketchy style
        if self._SKETCHY:
            make_context_sketchy(self.node.getContext("2d"))

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
        ev.type = (
            "touch_"
            + {
                "start": "down",
                "move": "move",
                "end": "up",
                "cancel": "up",
            }.get(e.type[5:])
        )
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
        # Get tooltip object - if text is None it means no tooltip
        ob = self._tooltips.pick(x, y)
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
                self._tooltipdiv.style.top = ob.rect[1] + "px"
                if x < self.w / 2:
                    self._tooltipdiv.style.left = ob.rect[2] + "px"
                    self._tooltipdiv.style.right = None
                else:
                    self._tooltipdiv.style.left = None
                    self._tooltipdiv.style.right = self.w - ob.rect[0] + "px"
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
            rect = self._tooltipdiv.rect
            self._tooltipdiv.style.transition = None
            self._tooltipdiv.style.opacity = 1
            self._tooltipdiv.style.top = rect[1] + "px"
            if self._tooltipdiv.style.left:
                self._tooltipdiv.style.left = rect[2] + 10 + "px"
            else:
                self._tooltipdiv.style.right = self.w - rect[0] + 10 + "px"

    def register_tooltip(self, x1, y1, x2, y2, text):
        ob = {"rect": [x1, y1, x2, y2], "text": text}
        self._tooltips.register(x1, y1, x2, y2, ob)

    # To overload

    def on_resize(self):
        pass

    def on_draw(self, ctx):
        pass

    def on_wheel(self, ev):
        pass

    def on_pointer(self, ev):
        pass


class AsyncStorage:
    """A kind of localstorage API, but async and without the 5MB memory
    restriction, based on IndexedDB.
    """

    _dbname = "timeturtle"
    _dbstorename = "cache"
    _dbversion = 1

    async def clear(self):
        """Async delete all items from the cache."""

        def executor(resolve, reject):
            on_error = lambda e: reject(self._error_msg(e))

            def on_db_ready(e):
                db = e.target.result
                db.onerror = on_error
                transaction = db.transaction([self._dbstorename], "readwrite")
                request = transaction.objectStore(self._dbstorename).clear()
                request.onsuccess = lambda: resolve(None)

            request = window.indexedDB.open(self._dbname, self._dbversion)
            request.onerror = on_error
            request.onupgradeneeded = self._on_update_required
            request.onsuccess = on_db_ready

        return await window.Promise(executor)

    async def setItem(self, ob):
        """Async put an object in the db."""
        if not ob.key:
            raise KeyError("Object must have a 'key' property")

        def executor(resolve, reject):
            on_error = lambda e: reject(self._error_msg(e))

            def on_db_ready(e):
                db = e.target.result
                db.onerror = on_error
                transaction = db.transaction([self._dbstorename], "readwrite")
                request = transaction.objectStore(self._dbstorename).put(ob)
                request.onsuccess = lambda: resolve(None)

            request = window.indexedDB.open(self._dbname, self._dbversion)
            request.onerror = on_error
            request.onupgradeneeded = self._on_update_required
            request.onsuccess = on_db_ready

        return await window.Promise(executor)

    async def getItem(self, key):
        """Async get an object from the db."""

        def executor(resolve, reject):
            on_error = lambda e: reject(self._error_msg(e))

            def on_db_ready(e):
                db = e.target.result
                db.onerror = on_error
                transaction = db.transaction([self._dbstorename], "readonly")
                request = transaction.objectStore(self._dbstorename).get(key)
                request.onsuccess = lambda e: resolve(e.target.result)

            request = window.indexedDB.open(self._dbname, self._dbversion)
            request.onerror = on_error
            request.onupgradeneeded = self._on_update_required
            request.onsuccess = on_db_ready

        return await window.Promise(executor)

    def _error_msg(self, e):
        msg = "IndexDB error"
        if e.target.errorCode:
            msg += " (" + e.target.errorCode + ")"
        if e.target.error:
            msg += ": " + e.target.error
        return msg

    def _on_update_required(self, e):
        # This is where we structure the database.
        # Gets called before db_open_request.onsuccess.
        db = e.target.result
        for i in range(len(db.objectStoreNames)):
            db.deleteObjectStore(db.objectStoreNames[i])
        db.createObjectStore(self._dbstorename, {"keyPath": "key"})


if __name__ == "__main__":
    import pscript

    pscript.script2js(
        __file__, target=__file__[:-3] + ".js", namespace="utils", module_type="simple"
    )
