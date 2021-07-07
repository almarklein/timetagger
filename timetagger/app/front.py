"""
Front end implementation in PScript.
"""

from pscript import this_is_js
from pscript.stubs import window, Math, time, perf_counter


if this_is_js():
    dt = window.dt
    utils = window.utils
    dialogs = window.dialogs
    BaseCanvas = window.utils.BaseCanvas
else:
    BaseCanvas = object


SMALLER = 0.85
BUTTON_ROUNDNESS = 4
RECORD_AREA_ROUNDNESS = 4
RECORD_ROUNDNESS = 6
COLORBAND_ROUNDNESS = 4
ANALYSIS_ROUNDNESS = 6

PI = 3.141_592_653_589_793

COLORS = {}

# These get updated when the canvas resizes
FONT = {
    "size": 16,
    "condensed": "Ubuntu Condensed, Arial, sans-serif",
    "wide": "Ubuntu, Arial, sans-serif",
    "mono": "Space Mono, Consolas, Monospace, Courier New",
    "default": "Ubuntu, Arial, sans-serif",
}


def init_module():
    set_colors()
    if window.matchMedia:
        try:
            window.matchMedia("(prefers-color-scheme: dark)").addEventListener(
                "change", set_colors
            )
        except Exception:
            pass  # e.g. Mobile Safari


window.addEventListener("load", init_module)


# Also see e.g. https://www.canva.com/colors/color-wheel/
def set_colors():

    # Dark vs light mode
    mode = mode = window.localsettings.get("darkmode", 1)
    if mode == 1:
        light_mode = True
    elif mode == 2:
        light_mode = False
    else:
        light_mode = True
        if window.matchMedia:
            if window.matchMedia("(prefers-color-scheme: dark)").matches:
                light_mode = False

    # Theme palette
    COLORS.prim1_clr = "#0F2C3E"
    COLORS.prim2_clr = "#A4B0B8"
    COLORS.sec1_clr = "#E6E7E5"
    COLORS.sec2_clr = "#F4F4F4"
    COLORS.acc_clr = "#DEAA22"

    # Grays chosen to work in both light and dark mode
    COLORS.tick_text = "rgba(130, 130, 130, 1)"
    COLORS.tick_stripe1 = COLORS.prim1_clr  # "rgba(130, 130, 130, 0.6)"  # day
    COLORS.tick_stripe2 = "rgba(130, 130, 130, 0.4)"  # major
    COLORS.tick_stripe3 = "rgba(130, 130, 130, 0.08)"  # minor

    if light_mode:
        COLORS.background1 = "rgba(244, 244, 244, 1)"  # == #f4f4f4  - must end in "1)"
        COLORS.top_bg = COLORS.prim1_clr

        COLORS.panel_bg = COLORS.sec1_clr
        COLORS.panel_edge = COLORS.prim1_clr

        COLORS.button_bg = "#fff"
        COLORS.button_shadow = "rgba(0, 0, 0, 0.4)"
        COLORS.button_text = COLORS.prim1_clr
        COLORS.button_text_disabled = COLORS.prim2_clr

        COLORS.record_bg = "#fafafa"
        COLORS.record_text = COLORS.prim1_clr
        COLORS.record_edge = COLORS.prim1_clr

        window.document.body.classList.remove("darkmode")

    else:
        # App background (use rgba so the color can be re-used with different alpha)
        COLORS.background1 = "rgba(23, 30, 40, 1)"  # must end in "1)"
        COLORS.top_bg = COLORS.prim1_clr

        COLORS.panel_bg = COLORS.prim1_clr
        COLORS.panel_edge = "#000"

        COLORS.button_bg = "#bbb"  # COLORS.prim2_clr
        COLORS.button_shadow = "rgba(0, 0, 0, 0.4)"
        COLORS.button_text = COLORS.prim1_clr
        COLORS.button_text_disabled = "#888"

        COLORS.record_bg = "rgb(50, 55, 62)"
        COLORS.record_text = "rgb(170, 170, 170)"
        COLORS.record_edge = "rgb(75, 75, 75)"

        window.document.body.classList.add("darkmode")
        # window.document.body.style.background = "rgb(0, 0, 0)"


def draw_tag(ctx, tag, x, y):
    """Like fillText, but colors the hashtag in the tag's color."""
    ori_color = ctx.fillStyle
    ctx.fillStyle = window.store.settings.get_color_for_tag(tag)
    ctx.fillText(tag[0], x, y)
    x += ctx.measureText(tag[0]).width
    ctx.fillStyle = ori_color
    ctx.fillText(tag[1:], x, y)


class TimeTaggerCanvas(BaseCanvas):
    """Main class for the time app. Does the layout and acts as the root
    application object.
    """

    def __init__(self, canvas):
        super().__init__(canvas)

        self._now = None

        self._last_picked_widget = None
        self._prefer_show_analytics = False

        self.range = TimeRange(self)

        self.notification_dialog = dialogs.NotificationDialog(self)
        self.menu_dialog = dialogs.MenuDialog(self)
        self.timeselection_dialog = dialogs.TimeSelectionDialog(self)
        self.settings_dialog = dialogs.SettingsDialog(self)
        self.record_dialog = dialogs.RecordDialog(self)
        self.tag_color_selection_dialog = dialogs.TagColorSelectionDialog(self)
        self.tag_color_dialog = dialogs.TagColorDialog(self)
        self.report_dialog = dialogs.ReportDialog(self)
        self.tag_preset_dialog = dialogs.TagPresetsDialog(self)
        self.tag_manage_dialog = dialogs.TagManageDialog(self)
        self.export_dialog = dialogs.ExportDialog(self)
        self.import_dialog = dialogs.ImportDialog(self)
        self.pomodoro_dialog = dialogs.PomodoroDialog(self)

        # The order here is also the draw-order. Records must come after analytics.
        self.widgets = {
            "AnalyticsWidget": AnalyticsWidget(self),
            "RecordsWidget": RecordsWidget(self),
            "TopWidget": TopWidget(self),
        }

        self.node.addEventListener("blur", self.on_blur)

    def _pick_widget(self, x, y):
        for widget in reversed(self.widgets.values()):
            x1, y1, x2, y2 = widget.rect
            if x1 <= x <= x2:
                if y1 <= y <= y2:
                    return widget

    def notify_once(self, message):
        """Notify the user once (for each session)."""
        cache = self._notification_cache or {}
        self._notification_cache = cache
        if message not in cache:
            cache[message] = True
            self.notification_dialog.open(message)

    def now(self):
        if self._now is not None:
            return self._now
        return dt.now()

    def on_resize(self):
        """Perform layout; set sizes of widgets. We can go all responsive here."""

        margin = 5
        space_to_divide = self.w - margin - margin
        if space_to_divide >= 785:
            margin2 = 40
            records_width = (space_to_divide - margin2) / 2
        else:
            margin2 = 5
            if self._prefer_show_analytics:
                records_width = 30
            else:
                records_width = (space_to_divide - margin2) - 30

        # Determine splitter positions
        #
        #   | records | | analytics |
        # 0 1         2 3           4 5

        x0 = 0
        x1 = margin
        x2 = x1 + records_width
        x3 = x2 + margin2
        x4 = self.w - margin
        x5 = self.w  # noqa

        x1 = self.grid_round(x1)
        x2 = self.grid_round(x2)
        x3 = self.grid_round(x3)
        x4 = self.grid_round(x4)

        y0 = 0
        y1 = self.grid_round(110)
        y2 = self.grid_round(140)
        y3 = self.grid_round(self.h - 15)

        self.widgets["TopWidget"].rect = x0, y0, x5, y1
        self.widgets["RecordsWidget"].rect = x1, y2, x2, y3
        self.widgets["AnalyticsWidget"].rect = x3, y2, x4, y3

        # Determine reference font
        FONT.default = FONT.condensed if self.w < 450 else FONT.wide

    def on_draw(self, ctx):

        # Set current moment as consistent reference for "now"
        self._now = dt.now()

        # Update the range if it is animating
        self.range.animation_update()

        # Clear / draw background
        ctx.clearRect(0, 0, self.w, self.h)
        # ctx.fillStyle = COLORS.background1
        # ctx.fillRect(0, 0, self.w, self.h)

        # Draw icon in bottom right
        iconw = 192 if self.w >= 400 else 96
        iconh = iconw / 6
        ctx.drawImage(
            window.document.getElementById("ttlogo_tg"),
            self.w - iconw - 5,
            self.h - iconh - 5,
            iconw,
            iconh,
        )

        # Determine if we are logged in and all is right (e.g. token not expired)
        cantuse = None
        if window.store.get_auth:
            auth = window.store.get_auth()
            if not auth:
                cantuse = "You are loged out."
            elif auth.cantuse:
                cantuse = auth.cantuse

        if cantuse:
            # Meh
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"
            ctx.fillStyle = COLORS.prim1_clr
            utils.fit_font_size(ctx, self.w - 100, FONT.default, cantuse, 30)
            ctx.fillText(cantuse, self.w / 2, self.h / 3)
            # Draw menu and login button
            ctx.save()
            try:
                self.widgets["TopWidget"].on_draw(ctx, True)  # menu only
            finally:
                ctx.restore()
        else:
            # Draw child widgets
            for widget in self.widgets.values():
                ctx.save()
                try:
                    widget.on_draw(ctx)
                finally:
                    ctx.restore()

        self._now = None  # Use real "now" in between draws

    def on_wheel(self, ev):
        w = self._pick_widget(*ev.pos)
        if w is not None:
            return w.on_wheel(ev)

    def on_pointer(self, ev):
        if "down" in ev.type and ev.ntouches == 1:
            self._last_picked_widget = self._pick_widget(*ev.pos)
        for widget in self.widgets.values():
            if widget is self._last_picked_widget:
                widget.on_pointer(ev)
            else:
                widget.on_pointer_outside(ev)

    def on_blur(self, ev):
        for widget in self.widgets.values():
            widget.on_pointer_outside(ev)


# The available scales to view the time at, and the corresponding step sizes
SCALES = [
    ("5m", "1m"),
    ("20m", "1m"),
    ("1h", "5m"),
    ("3h", "5m"),
    ("6h", "5m"),  # Kind of the default view
    ("12h", "1h"),
    ("1D", "1h"),
    ("1W", "1D"),  # step with 1D, 1W steps is awkward
    ("1M", "1D"),  # 1M steps bit awkward, but what else?
    ("3M", "1M"),
    ("1Y", "1M"),  # step per quarter of month?
    ("2Y", "1M"),
    ("5Y", "1Y"),
    ("10Y", "1Y"),
    ("20Y", "1Y"),
]

# List of intervals for tick marks. The last element is the number of seconds
# between two items, and is used to select an interval based on available pixel space.
# Major interval, minor interval, granularity for tick text, nsecs
INTERVALS = [
    ("1m", "10s", "mm", 60),
    ("2m", "10s", "mm", 120),
    ("5m", "1m", "mm", 300),
    ("10m", "1m", "mm", 600),
    ("30m", "5m", "mm", 1800),
    ("1h", "10m", "mm", 3600),
    ("2h", "15m", "mm", 7200),
    ("6h", "1h", "hh", 21600),
    ("12h", "1h", "hh", 43200),
    ("1D", "3h", "DD", 86400),
    ("2D", "6h", "DD", 172_800),
    ("5D", "1D", "DM", 432_000),
    ("10D", "1D", "DM", 864_000),
    # Below numbers are estimates, but that is fine;
    # they are only used to estimate the space between ticks
    ("1M", "5D", "MM", 2_592_000),  # days are a bit weird, ah well ...
    ("3M", "1M", "MM", 7_776_000),
    ("1Y", "1M", "YY", 31_536_000),
    ("1Y", "3M", "YY", 63_072_000),  # weird to show every other year
    ("5Y", "1Y", "YY", 157_680_000),
    ("10Y", "1Y", "YY", 315_360_000),
]


class TimeRange:
    """Object to keep track of the time range."""

    def __init__(self, canvas):
        self._canvas = canvas

        # The animate variable is normally None. During animation, it is a tuple
        self._animate = None

        # Init time to the current full day
        self._t1 = dt.floor(self._canvas.now(), "1D")
        self._t2 = dt.add(self._t1, "1D")
        self._t1, self._t2 = self.get_snap_range()  # snap non-animated

    def get_range(self):
        """Get the current time range (as a 2-element tuple, in seconds)."""
        return self._t1, self._t2

    def get_target_range(self):
        """Get the target range (where we're animating to). If no animation
        is in effect, this returns the same as get_range().
        """
        if self._animate is not None:
            (
                t1_old,
                t2_old,
                t1_new,
                t2_new,
                animation_time,
                animation_end,
                snap,
            ) = self._animate
            return t1_new, t2_new
        else:
            return self._t1, self._t2

    def set_range(self, t1, t2):
        """Set the time range to the target t1 and t2, canceling any animation in progress."""
        assert t1 < t2
        self._t1, self._t2 = t1, t2
        self._animate = None
        self._canvas.update()

    def animate_range(self, t1, t2, animation_time=None, snap=True):
        """Animate the time range to the target t1 and t2, over the given animation time."""
        # Going from high scale to low (or reverse) takes longer
        if animation_time is None:
            nsecs1, nsecs2 = t2 - t1, self._t2 - self._t1
            factor = max(nsecs1, nsecs2) / min(nsecs1, nsecs2)
            animation_time = 0.3 + 0.1 * Math.log(factor)

        animation_end = self._canvas.now() + animation_time  # not rounded to seconds!
        self._animate = self._t1, self._t2, t1, t2, animation_time, animation_end, snap
        self._canvas.update()

    def animation_update(self):
        """Set new range for the current animation (if there is one)."""
        if self._animate is None:
            return

        (
            t1_old,
            t2_old,
            t1_new,
            t2_new,
            animation_time,
            animation_end,
            snap,
        ) = self._animate
        now = self._canvas.now()

        if now >= animation_end:
            # Done animating
            self._t1, self._t2 = t1_new, t2_new
            self._animate = None
            if snap:
                self.snap()  # Will animate to aligned range if not already aligned
        else:
            # Interpolate the transition
            f = (animation_end - now) / animation_time
            # Scale the f-factor exponentially with the scaling of the time
            nsecs_old = t2_old - t1_old
            nsecs_new = t2_new - t1_new
            x = Math.log(2 + nsecs_old) / Math.log(2 + nsecs_new)
            x = x ** 2  # Otherwise higher scaler animate slower
            f = f ** x
            # Linear animation, or slower towards the end?
            # f = f ** 2
            self._t1 = f * t1_old + (1 - f) * t1_new
            self._t2 = f * t2_old + (1 - f) * t2_new
        self._canvas.update()

    def snap(self):
        """Snap to an aligned time range."""
        t1, t2 = self.get_target_range()
        t3, t4 = self.get_snap_range()
        if not (t1 == t3 and t2 == t4):
            self.animate_range(t3, t4)

    # Get range information

    def get_snap_range(self, scalestep=0):
        """Get the scale-aligned range that is closest to the current target range."""
        t3, t4, scale_index = self._get_snap_range(scalestep)
        return t3, t4

    def get_snap_seconds(self, rel_scale=0):
        """Get the nsecs for one step and the total range for the nearest
        snap range (or next/previous).
        """
        t1, t2, scale_index = self._get_snap_range(rel_scale)
        ran, res = SCALES[scale_index]
        nsecs_full = t2 - t1
        nsecs_step = dt.add(t1, res) - t1
        return nsecs_step, nsecs_full

    def _get_snap_range(self, scalestep=0):
        """Get the scale-aligned range that is closest to the current target range."""
        t1, t2 = self.get_target_range()
        nsecs = t2 - t1

        # First determine nearest scale
        min_dist = 1e18
        for i in range(len(SCALES)):
            ran, res = SCALES[i]
            t3 = dt.add(t1, ran)
            dist = Math.abs(1 - nsecs / (t3 - t1))
            if dist > min_dist:
                break
            min_dist = dist

        # Select scale
        scale_index = i - 1 + scalestep
        scale_index = max(0, min(len(SCALES) - 1, scale_index))
        ran, res = SCALES[scale_index]

        # Round
        t5 = 0.5 * (t1 + t2)  # center
        t3 = 0.5 * (t5 + dt.add(t5, "-" + ran))  # unrounded t3
        t3 = dt.round(t3, res)
        t4 = dt.add(t3, ran)
        return t3, t4, scale_index

    def get_ticks(self, npixels):
        """Get the major and minor tick positions,
        based on the available space and current time-range.
        """
        PSCRIPT_OVERLOAD = False  # noqa

        t1, t2 = self.get_range()
        nsecs = t2 - t1

        # We use a cache with 1 entry, so if the "tick-args" are the
        # same as last time, the result is re-used.
        cache_key = str((t1, t2, npixels))
        if not self._cache_tick_data:
            self._cache_tick_data = {}
        if cache_key == self._cache_tick_data.key:
            return self._cache_tick_data.result
        else:
            self._cache_tick_data.key = cache_key

        # Determine interval - distance between ticks depends on total size;
        # if there is a lot of space, its ugly to have loads of ticks
        pixelref = 4
        min_distance = pixelref * (npixels / pixelref) ** 0.5
        min_interval = nsecs * min_distance / npixels
        for i in range(len(INTERVALS)):
            delta, minor_delta, granularity, interval = INTERVALS[i]
            if interval > min_interval:
                break

        # Select minor scale from next level if we are close to it.
        # This results in a smoother transition, as minor and major ticks alternate jumps.
        if i < len(INTERVALS) - 1:
            if (interval - min_interval) / interval < 0.125:  # 0.25 is too soon
                minor_delta = INTERVALS[i + 1][1]

        # When within hour range, deal with the summer- to winter-time transtion.
        # There is a duplicate hour, which needs special care to make it ticked.
        # For the winter- to summer-time transition there is a missing hour,
        # which is handled just fine.
        check_summertime_transition = "h" in delta or "m" in delta

        # Define ticks
        ticks = []
        minor_ticks = []
        maxi = 2 * npixels / min_distance
        t = dt.floor(t1 - 0.1 * nsecs, delta)
        iter = -1
        while iter < maxi:  # just to be safe
            iter += 1
            pix_pos = (t - t1) * npixels / nsecs
            ticks.push((pix_pos, t))
            # Determine delta. The +1s and then floor is to take care
            # of the transition from wintertime to summertime.
            # Even then, t_new may still not advance for ios somehow (see #73).
            t_new = dt.floor(dt.add(t + 1, delta), delta)
            if t_new <= t:
                t_new = dt.add(t, delta)
            # Minor ticks
            t_minor = dt.add(t, minor_delta)
            while (t_new - t_minor) > 0:
                pix_pos = (t_minor - t1) * npixels / nsecs
                minor_ticks.push((pix_pos, t_minor))
                t_minor_new = dt.add(t_minor, minor_delta)
                if t_minor_new <= t_minor:
                    break  # failsafe
                t_minor = t_minor_new
            # Summertime transition?
            if check_summertime_transition and (t_new - t) > interval * 1.1:
                tc = dt.floor(t_new, "1D")
                for i in range(5):
                    tb = tc + 3600
                    tc = dt.add(tc, "1h")
                    if tc != tb:
                        # Add ticks at sumertime transition
                        tick_times = [tb] if t_new == tc else [tb, tc]
                        for tick_time in tick_times:
                            pix_pos = (tick_time - t1) * npixels / nsecs
                            ticks.push((pix_pos, tc))
                        # Add minor ticks at duplicate hour
                        d_minor = dt.add(t_new, minor_delta) - t_new
                        t_minor = tb + d_minor
                        while t_minor < tc:
                            pix_pos = (t_minor - t1) * npixels / nsecs + 3
                            minor_ticks.push((pix_pos, t_minor))
                            t_minor += d_minor
                        break
            # prepare for next
            if (t - t2) > 0:
                break
            t = t_new

        self._cache_tick_data.result = ticks, minor_ticks, granularity
        return self._cache_tick_data.result

    def get_stat_period(self):
        """Get the time period over which to display stats, given the current range."""
        # At some point we used get_snap_range(), so that the type of
        # record is a direct snap-hint. But it makes the animation from a large
        # nsecs to a small very slow, because a lot of stats will be drawn.
        t1, t2 = self.get_range()
        nsecs = t2 - t1
        if nsecs > 3 * 300 * 86400:
            stat_period = "1Y", "year"
        elif nsecs > 5 * 30 * 86400:
            stat_period = "3M", "quarter"
        elif nsecs > 2.6 * 20 * 86400:
            stat_period = "1M", "month"
        elif nsecs >= 10 * 86400:
            stat_period = "1W", "week"
        elif nsecs > 4.1 * 1 * 86400:
            stat_period = "1D", "day"
        else:
            stat_period = None, ""  # Don't draw stats, but records!
        return stat_period

    def get_context_header(self):
        """Get the text to provide context for the current range."""

        t1, t2 = self.get_range()
        nsecs = t2 - t1

        t2 -= 1

        day1 = dt.time2str(t1).split("T")[0]
        day2 = dt.time2str(t2).split("T")[0]

        # Get friendly stuff that we can display
        weekday1, weekday2 = dt.get_weekday_shortname(t1), dt.get_weekday_shortname(t2)
        monthname1, monthname2 = dt.get_month_shortname(t1), dt.get_month_shortname(t2)
        year1, month1, monthday1 = dt.get_year_month_day(t1)
        year2, month2, monthday2 = dt.get_year_month_day(t2)
        is_week_range = abs(nsecs - 86400 * 7) <= 4000  # var for summer/wintertime

        if day1 == day2:
            # Within a single day - finest granularity for the header
            header = f"{weekday1} {monthday1}  {monthname1} {year1}"
        elif day1[:7] == day2[:7]:
            # Within a single month
            if nsecs <= 86400 * 3:
                # Just 3 days - show weekdays
                header = f"{weekday1} {monthday1} - {weekday2} {monthday2}  {monthname1} {year1}"
            elif is_week_range and dt.is_first_day_of_week(t1):
                # Exactly a calender week
                wn = dt.get_weeknumber(t1)
                header = f"Week {wn}  {monthday1}-{monthday2}  {monthname1} {year1}"
            elif nsecs <= 86400 * 14:
                # Less than half a month
                header = f"{monthday1} - {monthday2}  {monthname1} {year1}"
            else:
                header = f"{monthname1}  {year1}"
        elif day1[:4] == day2[:4]:
            # Within a single year
            if is_week_range and dt.is_first_day_of_week(t1):
                # Exactly a calender week
                wn = dt.get_weeknumber(t1)
                header = f"Week {wn}  {monthname1} / {monthname2} {year1}"
            elif nsecs < 30 * 86400:
                # Less than one month
                header = f"{monthname1} / {monthname2}  {year1}"
            else:
                # Multi month
                header = f"{year1}"
                if day1[5:] == "01-01" and day2[5:] == "12-31":
                    pass
                elif day1[5:] == "01-01" and day2[5:] == "03-31":
                    header = f"Q1  {year1}"
                elif day1[5:] == "04-01" and day2[5:] == "06-30":
                    header = f"Q2  {year1}"
                elif day1[5:] == "07-01" and day2[5:] == "09-30":
                    header = f"Q3  {year1}"
                elif day1[5:] == "10-01" and day2[5:] == "12-31":
                    header = f"Q4  {year1}"
                else:
                    header = f"{monthname1} - {monthname2}  {year1}"
        else:
            # Multi-year
            if is_week_range and dt.is_first_day_of_week(t1):
                wn = dt.get_weeknumber(t1)
                header = f"Week {wn}  {monthname1} {year1} / {monthname2} {year2}"
            elif nsecs < 30 * 86400:  # Less than one month
                header = f"{monthname1} {year1} / {monthname2} {year2}"
            elif nsecs < 367 * 86400:  # Less than a year
                header = f"{monthname1} {year1} - {monthname2} {year2}"
            else:
                header = f"{year1} - {year2}"

        return header


class Widget:
    """Base Widget class."""

    def __init__(self, canvas):
        self._canvas = canvas
        self.rect = 0, 0, 0, 0  # (x1, y1, x2, y2) - Layout is done by the canvas
        self.on_init()

    def update(self):
        """Invoke a new draw."""
        self._canvas.update()

    def on_init(self):
        pass

    def on_wheel(self, ev):
        pass

    def on_pointer(self, ev):
        pass

    def on_pointer_outside(self, ev):
        pass

    def on_draw(self, ctx):
        pass

    def _draw_button(self, ctx, x, y, given_w, h, text, action, tt, options):
        PSCRIPT_OVERLOAD = False  # noqa

        # Set and collect options
        opt = {
            "font": FONT.default,
            "ref": "topleft",
            "color": COLORS.button_text,
            "padding": 7,
            "space": 5,
            "body": True,
        }
        opt.update(options)

        if text.toUpperCase:  # is string
            texts = [text]
        else:
            texts = list(text)

        # Measure texts
        widths = []
        fonts = []
        for i in range(len(texts)):
            text = texts[i]
            if text.startswith("fas-"):
                text = text[4:]
                font = int(0.5 * h) + "px FontAwesome"
            else:
                font = int(0.5 * h) + "px " + opt.font
            ctx.font = font
            width = ctx.measureText(text).width
            texts[i] = text
            fonts.push(font)
            widths.push(width)

        # Determine width
        needed_w = sum(widths) + 2 * opt.padding + opt.space * (len(widths) - 1)
        if given_w:
            w = given_w
            # scale = min(1, given_w / needed_w)
        else:
            w = needed_w
            # scale = 1

        # Determine bounding box
        if opt.ref.indexOf("right") >= 0:
            x2 = x
            x1 = x2 - w
        elif opt.ref.indexOf("center") >= 0:
            x1 = x - w / 2
            x2 = x + w / 2
        else:
            x1 = x
            x2 = x1 + w
        #
        if opt.ref.indexOf("bottom") >= 0:
            y2 = y
            y1 = y2 - h
        elif opt.ref.indexOf("middle") >= 0:
            y1 = y - h / 2
            y2 = y + h / 2
        else:
            y1 = y
            y2 = y1 + h

        # Draw button body and its shadow
        if opt.body:
            ctx.fillStyle = COLORS.button_bg
            rn = BUTTON_ROUNDNESS
            for i in range(2):
                dy = 2 if i == 0 else 0
                ctx.beginPath()
                ctx.arc(x1 + rn, y1 + dy + rn, rn, 1.0 * PI, 1.5 * PI)
                ctx.arc(x2 - rn, y1 + dy + rn, rn, 1.5 * PI, 2.0 * PI)
                ctx.arc(x2 - rn, y2 + dy - rn, rn, 0.0 * PI, 0.5 * PI)
                ctx.arc(x1 + rn, y2 + dy - rn, rn, 0.5 * PI, 1.0 * PI)
                ctx.closePath()
                if i == 0:
                    ctx.shadowBlur = 3
                    ctx.shadowColor = COLORS.button_shadow
                ctx.fill()
                ctx.shadowBlur = 0

        # Register the button and tooltip
        ob = {"button": True, "action": action}
        self._picker.register(x1, y1, x2, y2, ob)
        if tt:
            self._canvas.register_tooltip(x1, y1, x2, y2, tt, "below")

        # Get starting x
        x = x1 + opt.padding + 0.5 * (w - needed_w)

        # Draw the text on top
        ctx.textBaseline = "middle"
        ctx.textAlign = "left"
        ctx.fillStyle = opt.color
        for i in range(len(texts)):
            text, width, font = texts[i], widths[i], fonts[i]
            ctx.font = font
            if text.startsWith("#"):
                draw_tag(ctx, text, x, 0.5 * (y1 + y2))
            else:
                ctx.fillText(text, x, 0.5 * (y1 + y2))
            x += width + opt.space

        return w


class TopWidget(Widget):
    """Widget with menu, buttons, and time header."""

    def on_init(self):
        self._picker = utils.Picker()
        self._button_pressed = None
        self._current_scale = {}
        self._sync_feedback_xy = 0, 0
        window.setInterval(self._draw_sync_feedback_callback, 100)

        # For navigation with keys. Listen to canvas events, and window events (in
        # case canvas does not have focus), but don't listen for events from dialogs.
        window.addEventListener("keydown", self._on_key, 0)
        self._canvas.node.addEventListener("keydown", self._on_key, 0)

    def on_draw(self, ctx, menu_only=False):

        self._picker.clear()
        x1, y1, x2, y2 = self.rect

        y4 = y2  # noqa - bottom
        y2 = y1 + 50
        y3 = y2 + 12

        h = 36

        # Dark background wave (a cosine with the belly in the middle)
        ctx.beginPath()
        n = 20
        amplitude = 3
        period = 1.2 * 2 * PI
        ctx.moveTo(x2 + 50, y2)
        ctx.lineTo(x2 + 50, y1 - 50)
        ctx.lineTo(x2, y1 - 50)
        ctx.lineTo(x1, y1 - 50)
        ctx.lineTo(x1 - 50, y1 - 50)
        ctx.lineTo(x1 - 50, y2)
        for i in range(n + 1):
            x = x1 + i * (x2 - x1) / n
            y = y2 - amplitude * Math.cos(period * (i / n - 0.5))
            ctx.lineTo(x, y)
        ctx.closePath()

        ctx.fillStyle = COLORS.top_bg
        ctx.fill()

        self._margin = margin = self._canvas.grid_round(max(2, (x2 - x1) / 30))
        x = x1 + 4

        # Draw icon in top-right
        iconsize = (x2 - x1) / 22
        iconsize = 48
        if iconsize:
            ctx.drawImage(
                window.document.getElementById("ttlogo_sl"),
                x2 - iconsize,
                y1 + 2,
                iconsize,
                iconsize,
            )

        # Always draw the menu button
        self._draw_menu_button(ctx, x, y1, x2, y2)

        # If menu-only, also draw login, then exit
        if menu_only:
            self._draw_button(
                ctx,
                0.5 * (x1 + x2),
                y3,
                None,
                h,
                "Login",
                "login",
                "",
                {"ref": "topcenter"},
            )
            return

        # Draw some more inside dark banner
        self._draw_header_text(ctx, 60, y1, x2 - 60, y2 - 5)

        # Draw buttons below the dark banner
        # We go from the center to the sides
        xc = 0.5 * (x1 + x2)

        # Draw arrows
        ha = 0.6 * h
        yc = y3 + h / 2
        dx = self._draw_button(
            ctx,
            xc,
            yc - 1.5,
            h,
            ha,
            "fas-\uf077",
            "nav_backward",
            "Step backward [↑/pageUp]",
            {"ref": "bottomcenter"},
        )
        dx = self._draw_button(
            ctx,
            xc,
            yc + 1.5,
            h,
            ha,
            "fas-\uf078",
            "nav_forward",
            "Step forward [↓/pageDown]",
            {"ref": "topcenter"},
        )

        # -- move to the left

        x = xc - dx / 2 - 3

        now_scale, now_clr = self._get_now_scale()
        today_w = self._draw_button(
            ctx,
            x,
            y3,
            None,
            h,
            "Today",
            "nav_snap_now" + now_scale,
            "Snap to now [Home]",
            {"ref": "topright", "color": now_clr, "font": FONT.condensed},
        )

        x -= today_w + margin

        self._draw_tracking_buttons(ctx, x, y3, h)

        # -- move to the right

        x = xc + dx / 2 + 3

        x += self._draw_button(
            ctx,
            x,
            y3,
            today_w,
            h,
            ["fas-\uf073", "fas-\uf0d7"],
            "nav_menu",
            "Select time range [t]",
            {"ref": "topleft"},
        )

        x += margin

        x += self._draw_button(
            ctx,
            x,
            y3,
            None,
            h,
            ["fas-\uf15c", "Report"],
            "report",
            "Show report [r]",
            {"ref": "topleft", "font": FONT.condensed},
        )

    def _draw_menu_button(self, ctx, x1, y1, x2, y2):

        if window.store.__name__.startswith("Demo"):
            text = "Demo"
        elif window.store.__name__.startswith("Sandbox"):
            text = "Sandbox"
        else:
            text = ""

        dx = self._draw_sync_feedback(ctx, 4, 4)

        x = x1 + dx + 24

        opt = {
            "body": False,
            "padding": 4,
            "ref": "centermiddle",
            "color": COLORS.sec2_clr,
        }
        self._draw_button(ctx, x, y1 + 18, None, 48, "fas-\uf0c9", "menu", "", opt)

        # Draw title
        if text:
            ctx.textAlign = "center"
            ctx.textBaseline = "top"
            ctx.font = "12px " + FONT.default
            ctx.fillStyle = COLORS.acc_clr
            ctx.fillText(text, x, 34)

        return x - x1

    def _draw_sync_feedback(self, ctx, x1, y1):
        self._sync_feedback_xy = x1, y1
        return self._draw_sync_feedback_work()

    def _draw_sync_feedback_callback(self):
        self._draw_sync_feedback_work(False)

    def _draw_sync_feedback_work(self, register=True):
        PSCRIPT_OVERLOAD = False  # noqa

        if window.document.hidden:
            return

        ctx = self._canvas.node.getContext("2d")
        x, y = self._sync_feedback_xy

        # Get factor 0..1
        factor = window.store.sync_time
        factor = max(0, (factor[1] - dt.now()) / (factor[1] - factor[0] + 0.0001))
        factor = max(0, 1 - factor)

        radius = 7
        ctx.lineWidth = 2

        # Clear bg
        ctx.beginPath()
        ctx.arc(x + radius, y + radius, radius + ctx.lineWidth, 0, 2 * PI)
        ctx.fillStyle = COLORS.top_bg
        ctx.fill()

        # Outline
        ctx.beginPath()
        ctx.arc(x + radius, y + radius, radius, 0, 2 * PI)
        ctx.strokeStyle = "rgba(255, 255, 255, 0.3)"
        ctx.stroke()

        # Progress
        ref_angle = -0.5 * PI
        ctx.beginPath()
        ctx.arc(x + radius, y + radius, radius, ref_angle, ref_angle + factor * 2 * PI)
        ctx.strokeStyle = COLORS.prim2_clr
        ctx.stroke()

        # Draw indicator icon - rotating when syncing
        M = dict(
            pending="\uf067",  # uf067 uf055
            sync="\uf2f1",
            ok="\uf560",  # uf560 uf00c
            warn="\uf12a",
            error="\uf00d",
        )
        state = window.store.state
        text = M.get(state, "\uf00c")
        if text:
            ctx.save()
            try:
                ctx.translate(x + radius, y + radius)
                if state == "sync":
                    ctx.rotate(((0.5 * time()) % 1) * 2 * PI)
                ctx.font = (radius * 1.2) + "px FontAwesome"
                ctx.textBaseline = "middle"
                ctx.textAlign = "center"
                ctx.fillStyle = COLORS.prim2_clr
                ctx.fillText(text, 0, 0)
            finally:
                ctx.restore()

        # Register tiny sync button
        if register:
            ob = {"button": True, "action": "refresh", "help": ""}
            self._picker.register(
                x - 1, y - 1, x + radius * 2 + 1, y + radius * 2 + 1, ob
            )

        return 2 * radius

    def _draw_tracking_buttons(self, ctx, x, y, h):
        PSCRIPT_OVERLOAD = False  # noqa

        now = self._canvas.now()

        start_tt = "Start recording [s]"
        stop_tt = "Stop recording [x]"

        # Define stop summary
        running_summary = ""
        records = window.store.records.get_running_records()
        has_running = False
        if len(records) > 0:
            has_running = True
            running_summary = "Timers running"
            if len(records) == 1:
                tagz = window.store.records.tags_from_record(records[0]).join(" ")
                stop_tt += " " + tagz
                if window.localsettings.get("show_stopwatch", True):
                    running_summary = dt.duration_string(now - records[0].t1, True)
                    pomo = self._canvas.pomodoro_dialog.time_left()
                    if pomo:
                        running_summary = pomo + " | " + running_summary
                else:
                    running_summary = "Timer running"

        x0 = x

        # Start & stop button
        if has_running:
            dx = self._draw_button(
                ctx,
                x,
                y,
                h,
                h,
                "fas-\uf04d",
                "record_stopall",
                stop_tt,
                {"ref": "topright", "font": FONT.condensed},
            )
            x -= dx + 3
            dx = self._draw_button(
                ctx,
                x,
                y,
                h,
                h,
                "fas-\uf04b",
                "record_start",
                start_tt,
                {"ref": "topright", "font": FONT.condensed},
            )
            x -= dx
        else:
            dx = self._draw_button(
                ctx,
                x,
                y,
                None,
                h,
                ["fas-\uf04b", "Record"],
                "record_start",
                start_tt,
                {"ref": "topright", "font": FONT.condensed},
            )
            x -= dx

        # Pomodoro button
        if window.localsettings.get("pomodoro_enabled", False):
            x -= 3
            dx = self._draw_button(
                ctx,
                x,
                y,
                None,
                h,
                "fas-\uf2f2",
                "pomo",
                "Show Pomodoro dialog",
                {"ref": "topright", "font": FONT.condensed},
            )
            x -= dx

        # Draw summary text
        ctx.textBaseline = "top"
        ctx.textAlign = "center"
        ctx.font = "12px " + FONT.default
        ctx.fillStyle = COLORS.prim2_clr
        ctx.fillText(running_summary, (x0 + x) / 2, y + h + 5)

        return x0 - x

    def _get_now_scale(self, ctx):

        t1, t2 = self._canvas.range.get_range()  # get_snap_range()
        nsecs = t2 - t1
        now = self._canvas.now()

        # Get the "sensible" scale that is closest to the current scale
        if nsecs < 3 * 86400:
            now_scale = "1D"
        elif nsecs < 14 * 86400:
            now_scale = "1W"
        elif nsecs <= 45 * 86400:
            now_scale = "1M"
        elif nsecs <= 180 * 86400:
            now_scale = "3M"
        else:
            now_scale = "1Y"

        # Are we currently on one of the reference scales?
        now_clr = COLORS.button_text
        if len(now_scale):
            t1_now = dt.floor(now, now_scale)
            if t1 == t1_now and t2 == dt.add(t1_now, now_scale):
                now_clr = COLORS.button_text_disabled

        # Get where we should zoom in to
        # Use a margin for summer-winter transitions and leap days/secs.
        factor = 1.05
        if nsecs <= 86400 * factor:
            zoom_in_scale = "-1"
        elif nsecs <= 7 * 86400 * factor:
            zoom_in_scale = "1D"
        elif nsecs <= 31 * 86400 * factor:
            zoom_in_scale = "1W"
        elif nsecs <= 92 * 86400 * factor:
            zoom_in_scale = "1M"
        elif nsecs <= 365 * 86400 * factor:
            zoom_in_scale = "3M"
        elif nsecs <= 2 * 365 * 86400 * factor:
            zoom_in_scale = "1Y"
        else:
            zoom_in_scale = "-1"

        # Get where we should zoom out to.
        factor = 1 / 1.05
        if nsecs < 6 * 3600:
            zoom_out_scale = "+1"
        elif nsecs < 86400 * factor:
            zoom_out_scale = "1D"
        elif nsecs < 7 * 86400 * factor:
            zoom_out_scale = "1W"
        elif nsecs < 28 * 86400 * factor:
            zoom_out_scale = "1M"
        elif nsecs < 90 * 86400 * factor:  # min #days in 3 consecutive months
            zoom_out_scale = "3M"
        elif nsecs < 365 * 86400 * factor:
            zoom_out_scale = "1Y"
        else:
            zoom_out_scale = "+1"

        # Store for later
        self._current_scale["now"] = now_scale
        self._current_scale["in"] = zoom_in_scale
        self._current_scale["out"] = zoom_out_scale

        return now_scale, now_clr

    def _draw_header_text(self, ctx, x1, y1, x2, y2):

        header = self._canvas.range.get_context_header() + " "  # margin

        x3 = (x1 + x2) / 2
        y3 = y1 + 3

        # Draw header
        ctx.textBaseline = "top"
        ctx.textAlign = "center"
        #
        size = utils.fit_font_size(ctx, x2 - x1, FONT.default, header, 36)
        text1, _, text2 = header.partition("  ")
        if len(text2) == 0:
            # One part
            ctx.fillStyle = COLORS.sec2_clr
            ctx.fillText(header, x3, y3)
        elif size < 20:
            # Two parts below each-other
            size = utils.fit_font_size(ctx, x2 - x1, FONT.default, text2, 20)
            ctx.fillStyle = COLORS.acc_clr
            ctx.fillText(text1 + " ", x3, y3)
            ctx.fillStyle = COLORS.sec2_clr
            ctx.fillText(text2, x3, y1 + 5 + 18)
        else:
            # Two parts next to each-other
            text1 += "  "
            w1 = ctx.measureText(text1).width
            w2 = ctx.measureText(text2).width
            w = w1 + w2
            ctx.textAlign = "left"
            ctx.fillStyle = COLORS.acc_clr
            ctx.fillText(text1, x3 - w / 2, y3)
            ctx.fillStyle = COLORS.sec2_clr
            ctx.fillText(text2, x3 - w / 2 + w1, y3)

    def on_pointer(self, ev):
        x, y = ev.pos[0], ev.pos[1]
        if "down" in ev.type:
            picked = self._picker.pick(x, y)
            if picked is not None and picked.button:
                self._button_pressed = picked
                self.update()
        elif "up" in ev.type:
            self.update()
            pressed = self._button_pressed
            self._button_pressed = None
            picked = self._picker.pick(x, y)
            if pressed is not None and picked is not None:
                if picked.action == pressed.action:
                    self._handle_button_press(picked.action)

    def _on_key(self, e):
        if e.ctrlKey or e.metaKey or e.altKey:
            return  # don't fight with the browser
        elif e.key.lower() == "arrowup" or e.key.lower() == "pageup":
            self._handle_button_press("nav_backward")
        elif e.key.lower() == "arrowdown" or e.key.lower() == "pagedown":
            self._handle_button_press("nav_forward")
        elif e.key.lower() == "arrowleft":
            self._handle_button_press("nav_zoom_" + self._current_scale["out"])
        elif e.key.lower() == "arrowright":
            self._handle_button_press("nav_zoom_" + self._current_scale["in"])
        elif e.key.lower() == "home" or e.key.lower() == "end":
            self._handle_button_press("nav_snap_now" + self._current_scale["now"])
        #
        elif e.key.lower() == "d":
            self._handle_button_press("nav_snap_now1D")
        elif e.key.lower() == "w":
            self._handle_button_press("nav_snap_now1W")
        elif e.key.lower() == "m":
            self._handle_button_press("nav_snap_now1M")
        elif e.key.lower() == "t":
            self._handle_button_press("nav_menu")
        #
        elif e.key.lower() == "s":
            self._handle_button_press("record_start")
        elif e.key.lower() == "x":
            self._handle_button_press("record_stopall")
        elif e.key.lower() == "r":
            self._handle_button_press("report")
        else:
            return
        e.preventDefault()

    def _handle_button_press(self, action):
        now = self._canvas.now()

        if action == "menu":
            self._canvas.menu_dialog.open()

        elif action == "login":
            window.location.href = "../login"

        elif action == "refresh":
            window.store.sync_soon(0.2)

        elif action == "report":
            t1, t2 = self._canvas.range.get_range()
            tags = self._canvas.widgets.AnalyticsWidget.selected_tags
            self._canvas.report_dialog.open(t1, t2, tags)

        elif action == "pomo":
            self._canvas.pomodoro_dialog.open()

        elif action.startswith("record_"):
            # A time tracking action
            if action == "record_start":
                record = window.store.records.create(now, now)
                self._canvas.record_dialog.open("Start", record, self.update)
            elif action == "record_new":
                record = window.store.records.create(now - 1800, now)
                self._canvas.record_dialog.open("New", record, self.update)
            elif action == "record_stop":
                records = window.store.records.get_running_records()
                if len(records) > 0:
                    record = records[0]
                    record.t2 = max(record.t1 + 10, now)
                    self._canvas.record_dialog.open("Stop", record, self.update)
            elif action == "record_stopall":
                records = window.store.records.get_running_records()
                for record in records:
                    record.t2 = max(record.t1 + 10, now)
                    window.store.records.put(record)
                if window.localsettings.get("pomodoro_enabled", False):
                    self._canvas.pomodoro_dialog.stop()

        elif action.startswith("nav_"):
            # A navigation action
            if action.startswith("nav_snap_"):
                res = action.split("_")[-1]
                t1, t2 = self._canvas.range.get_target_range()
                if res.startswith("now"):
                    res = res[3:]
                    if len(res) == 0:
                        nsecs = t2 - t1
                        t1 = now - nsecs / 2
                        t2 = now + nsecs / 2
                    else:
                        t1 = dt.floor(now, res)
                        t2 = dt.add(t1, res)
                else:
                    t_ref = now if (t1 <= now <= t2) else (t2 + t1) / 2
                    t1 = dt.floor(t_ref, res)
                    t2 = dt.add(t1, res)
                self._canvas.range.animate_range(t1, t2)
            elif action.startswith("nav_zoom_"):
                t1, t2 = self._canvas.range.get_target_range()
                res = action.split("_")[-1]
                now_is_in_range = t1 <= now <= t2
                if res == "-1" or res == "+1":
                    if res == "-1":
                        t1, t2 = self._canvas.range.get_snap_range(-1)
                    else:
                        t1, t2 = self._canvas.range.get_snap_range(+1)
                    if now_is_in_range:
                        t1, t2 = now - 0.5 * (t2 - t1), now + 0.5 * (t2 - t1)
                else:
                    t_ref = now if (t1 <= now <= t2) else (t2 + t1) / 2
                    t1 = dt.floor(t_ref, res)
                    t2 = dt.add(t1, res)
                self._canvas.range.animate_range(t1, t2)
            elif action == "nav_backward" or action == "nav_forward":
                t1, t2 = self._canvas.range.get_target_range()
                nsecs = t2 - t1
                if nsecs < 80000:
                    if action == "nav_backward":
                        self._canvas.range.animate_range(t1 - nsecs, t1, None, False)
                    else:
                        self._canvas.range.animate_range(t2, t2 + nsecs, None, False)
                else:
                    res = self._current_scale["now"]
                    if action == "nav_backward":
                        res = "-" + res
                    t1 = dt.add(t1, res)
                    t2 = dt.add(t2, res)
                    self._canvas.range.animate_range(t1, t2, None, False)
            elif action == "nav_menu":
                self._canvas.timeselection_dialog.open()


class RecordsWidget(Widget):
    """Widget that draws the records, ticks, handles record
    manipulation, and timeline navigation.
    """

    def on_init(self):
        self._picker = utils.Picker()

        # Stuff related to records
        self._selected_record = None
        self._can_interact_with_records = False
        self._record_times = {}  # For snapping

        # Stuff related to interaction
        self._interaction_mode = 0
        self._last_pointer_down_event = None

        self._last_scale_scroll = 0
        self._last_trans_scroll = 0
        self._pointer_pos = {}
        self._pointer_startpos = {}
        self._pointer_startrange = 0, 0
        self._pointer_inertia = []  # track last n move events

    def on_draw(self, ctx):
        x1, y1, x2, y2 = self.rect
        self._picker.clear()

        # If too little space, only draw button to expand
        if x2 - x1 <= 50:
            width = 30
            x3, x4 = 0, width
            height = max(200, 0.33 * (y2 - y1))
            y3, y4 = (y1 + y2) / 2 - height / 2, (y1 + y2) / 2 + height / 2
            ctx.beginPath()
            ctx.moveTo(x3, y3)
            ctx.lineTo(x4, y3 + width)
            ctx.lineTo(x4, y4 - width)
            ctx.lineTo(x3, y4)
            ctx.fillStyle = COLORS.tick_stripe2
            ctx.fill()
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"
            ctx.fillStyle = COLORS.prim1_clr
            ctx.font = FONT.size + "px " + FONT.default
            for i, c in enumerate("Records"):
                ctx.fillText(c, (x3 + x4) / 2, (y3 + y4) / 2 + (i - 3) * 18)
            self._picker.register(
                x3, y3, x4, y4, {"button": True, "action": "showrecords"}
            )
            return

        x3 = self._canvas.grid_round(x1 + 64)
        x4 = self._canvas.grid_round(x3 + 50)

        # Draw background of "active region"
        ctx.fillStyle = COLORS.panel_bg
        ctx.fillRect(x3, y1, x4 - x3, y2 - y1)

        self._help_text = ""

        self._draw_ticks(ctx, x3, y1, x4, y2)
        self._draw_edge(ctx, x3, y1, x4, y2)
        self._draw_record_area(ctx, x3, x4, x2, y1, y2)
        ctx.clearRect(0, 0, x2, y1 - 33)
        self._draw_top_and_bottom_cover(ctx, x1, x3, x4, x2, y1 - 50, y1, 0.333)
        self._draw_top_and_bottom_cover(ctx, x1, x3, x4, x2, y2, self._canvas.h, -0.02)

        # Draw title text
        if self._canvas.w > 700:
            text1 = "Timeline"
            text2 = self._help_text
            ctx.textAlign = "left"
            ctx.textBaseline = "top"
            #
            ctx.font = "bold " + (FONT.size * 1.4) + "px " + FONT.mono
            ctx.fillStyle = COLORS.prim2_clr
            ctx.fillText(text1, 10, 65)
            #
            ctx.font = (FONT.size * 0.9) + "px " + FONT.default
            ctx.fillStyle = COLORS.prim2_clr
            ctx.fillText(text2, 10, 90)

    def _draw_edge(self, ctx, x1, y1, x2, y2):
        def drawstrokerect(lw):
            rn = RECORD_AREA_ROUNDNESS + lw
            ctx.beginPath()
            ctx.arc(x2 - rn + lw, y1 + rn - lw, rn, 1.5 * PI, 2.0 * PI)
            ctx.arc(x2 - rn + lw, y2 - rn + lw, rn, 0.0 * PI, 0.5 * PI)
            ctx.arc(x1 + rn - lw, y2 - rn + lw, rn, 0.5 * PI, 1.0 * PI)
            ctx.arc(x1 + rn - lw, y1 + rn - lw, rn, 1.0 * PI, 1.5 * PI)
            ctx.closePath()
            ctx.stroke()

        lw = 3
        ctx.lineWidth = lw
        ctx.strokeStyle = COLORS.background1
        drawstrokerect(1.0 * lw)
        ctx.strokeStyle = COLORS.panel_edge
        drawstrokerect(0.0 * lw)

    def _draw_top_and_bottom_cover(self, ctx, x1, x2, x3, x4, y1, y2, stop):
        grd1 = ctx.createLinearGradient(x1, y1, x1, y2)
        grd2 = ctx.createLinearGradient(x1, y1, x1, y2)
        # grd3 = ctx.createLinearGradient(x1, y1, x1, y2)
        color1 = COLORS.background1
        color2 = color1.replace("1)", "0.0)")
        color4 = color1.replace("1)", "0.7)")
        if stop > 0:
            grd1.addColorStop(0.0, color2)
            grd1.addColorStop(stop, color1)
            grd1.addColorStop(1.0, color2)
            grd2.addColorStop(0.0, color2)
            grd2.addColorStop(stop, color1)
            grd2.addColorStop(1.0, color4)
        else:
            grd1.addColorStop(0.0, color2)
            grd1.addColorStop(1 + stop, color1)
            grd1.addColorStop(1.0, color1)
            grd2.addColorStop(0.0, color4)
            grd2.addColorStop(1 + stop, color1)
            grd2.addColorStop(1.0, color1)
        ctx.fillStyle = grd1
        ctx.fillRect(0, y1, x4, y2 - y1)
        ctx.fillStyle = grd2
        ctx.fillRect(x2, y1, x4 - x2, y2 - y1 - 2)

    def _draw_ticks(self, ctx, x1, y1, x2, y2):
        PSCRIPT_OVERLOAD = False  # noqa
        t1, t2 = self._canvas.range.get_range()

        # Determine deltas
        npixels = y2 - y1  # number if logical pixels we can use
        nsecs = t2 - t1  # Number of seconds in our range

        # Define ticks
        ticks, minor_ticks, granularity = self._canvas.range.get_ticks(npixels)

        # Prepare for drawing ticks
        ctx.fillStyle = COLORS.tick_text
        ctx.font = (SMALLER * FONT.size) + "px " + FONT.default
        ctx.textBaseline = "middle"
        ctx.textAlign = "right"

        # Draw tick texts
        for pos, t in ticks:
            text = dt.time2localstr(t)
            year, month, monthday = dt.get_year_month_day(t)
            if granularity == "mm":
                text = text[11:16]
                if text == "00:00":
                    text = dt.get_weekday_shortname(t) + " " + monthday
                    if monthday == 1:
                        text += " " + dt.get_month_shortname(t)
                    text += " 0h"
            elif granularity == "hh":
                text = text[11:13].lstrip("0") + "h"
                if text == "h":
                    text = dt.get_weekday_shortname(t) + " " + monthday
                    if monthday == 1:
                        text += " " + dt.get_month_shortname(t)
                    text += " 0h"
            elif granularity == "DD":
                text = dt.get_weekday_shortname(t) + " " + monthday
                if monthday == 1:
                    text += " " + dt.get_month_shortname(t)
            elif granularity == "DM":
                text = monthday + " " + dt.get_month_shortname(t)
                if monthday == 1 and month == 1:
                    text += " " + year
            elif granularity == "MM":
                text = dt.get_month_shortname(t)
                if month == 1:  # i.e. Januari
                    text += " " + year
            elif granularity == "YY":
                text = str(year)
            ctx.fillText(text, x1 - 4, pos + y1, x1 - 3)

        # Draw tick stripes
        ctx.strokeStyle = COLORS.tick_stripe2
        ctx.lineWidth = 1
        ctx.beginPath()
        for pos, text in ticks:
            ctx.moveTo(x1, pos + y1, True)
            ctx.lineTo(x2, pos + y1, True)
        ctx.stroke()

        # Draw minor tick stripes
        ctx.strokeStyle = COLORS.tick_stripe3
        ctx.lineWidth = 1
        ctx.beginPath()
        for pos, text in minor_ticks:
            ctx.moveTo(x1, pos + y1, True)
            ctx.lineTo(x2, pos + y1, True)
        ctx.stroke()

        # Draw snap feedback
        if False:
            t1_snap, t2_snap = self._canvas.range.get_snap_range()
            y1_snap = (t1_snap - t1) * npixels / nsecs  # can be negative!
            y2_snap = (t2_snap - t1) * npixels / nsecs
            # diff = abs(y1_snap) + abs(y2_snap - npixels)
            # w = max(1, min(5, diff**0.5)) # feels "jerky"
            w = 0 if (t1_snap == t1 and t2_snap == t2) else 3
            if w > 0:
                ctx.fillStyle = COLORS.tick_stripe2
                ctx.fillRect(x2 + 2, y1 + y1_snap, w, y2_snap - y1_snap)

    def _draw_record_area(self, ctx, x1, x2, x3, y1, y2):

        t1, t2 = self._canvas.range.get_range()

        # Determine whether to draw records or stats, and how many
        npixels = y2 - y1
        nsecs = t2 - t1
        pps = npixels / nsecs
        stat_period, stat_name = self._canvas.range.get_stat_period()

        # Draw records or stats
        if stat_period is None:
            self._can_interact_with_records = True
            # Draw day boundaries
            t3 = dt.floor(t1, "1D")
            t4 = dt.add(dt.floor(t2, "1D"), "1D")
            ctx.lineWidth = 2
            ctx.strokeStyle = COLORS.tick_stripe1
            ctx.beginPath()
            while t3 <= t4:
                y = y1 + (t3 - t1) * pps
                ctx.moveTo(x1, y)
                ctx.lineTo(x2, y)
                t3 = dt.add(t3, "1D")
            ctx.stroke()
            # Draw records themselves
            self._draw_records(ctx, x1, x2, x3, y1, y2)
        else:
            self._help_text = "click on a " + stat_name + " to zoom"
            self._can_interact_with_records = False
            t3 = dt.floor(t1, stat_period)
            while t3 < t2:
                t4 = dt.add(t3, stat_period)
                y3 = y1 + (t3 - t1) * pps
                y4 = y1 + (t4 - t1) * pps
                self._picker.register(
                    x1, y3, x3, y4, {"statrect": True, "t1": t3, "t2": t4}
                )
                # self._draw_stats(ctx, t3, t4, x1+10, y3, x3-10, y4, stat_period)
                self._draw_stats(ctx, t3, t4, x2, y3, x3, y4, stat_period)
                ctx.lineWidth = 2
                ctx.strokeStyle = COLORS.tick_stripe1
                ctx.beginPath()
                ctx.moveTo(x1, y3)
                ctx.lineTo(x3, y3)
                ctx.stroke()
                t3 = t4
            # Put border around
            rn = RECORD_AREA_ROUNDNESS
            ctx.beginPath()
            ctx.arc(x3 - rn, y1 + rn, rn, 1.5 * PI, 2.0 * PI)
            ctx.arc(x3 - rn, y2 - rn, rn, 0.0 * PI, 0.5 * PI)
            ctx.arc(x2 + rn, y2 - rn, rn, 0.5 * PI, 1.0 * PI)
            ctx.arc(x2 + rn, y1 + rn, rn, 1.0 * PI, 1.5 * PI)
            ctx.closePath()
            ctx.lineWidth = 3
            ctx.strokeStyle = COLORS.prim1_clr
            ctx.stroke()

        # Draw "now" - also if drawing stats
        t = self._canvas.now()
        y = y1 + (t - t1) * pps
        ctx.strokeStyle = COLORS.prim1_clr
        ctx.lineWidth = 3  # Pretty thick so it sticks over other edges like week bounds
        ctx.setLineDash([4, 4])
        ctx.lineDashOffset = t % 8
        ctx.beginPath()
        ctx.moveTo(x1, y)
        ctx.lineTo(x2, y)
        ctx.stroke()
        ctx.setLineDash([])
        ctx.lineDashOffset = 0

    def _draw_records(self, ctx, x1, x2, x3, y1, y2):
        PSCRIPT_OVERLOAD = False  # noqa

        y0, y3 = y1 - 50, self._canvas.h
        t1, t2 = self._canvas.range.get_range()
        now = self._canvas.now()

        # Get range, in seconds and pixels for the time range
        npixels = y2 - y1  # number if logical pixels we can use
        nsecs = t2 - t1

        # Get whether we're "snapped". If so we'll align our horizontal lines
        t1_snap, t2_snap = self._canvas.range.get_snap_range()
        self._round_top_bottom = t1 == t1_snap and t2 == t2_snap

        # We will actually draw a larger range, because we show some of the future and past
        t1 -= (y1 - y0) * nsecs / npixels
        t2 += (y3 - y2) * nsecs / npixels
        nsecs = t2 - t1
        npixels = y3 - y0

        # Select all records in this range. Sort so that smaller records are drawn on top.
        records = window.store.records.get_records(t1, t2).values()

        if len(records) > 0:
            self._help_text = "click a record to edit it"

        # Sort records by size, so records cannot be completely overlapped by another
        records.sort(key=lambda r: r.t1 - (now if (r.t1 == r.t2) else r.t2))

        # Prepare by collecting stuff per record, and determine selected record
        self._record_times = {}
        positions_map = {}
        selected_record = None
        for record in records:
            self._record_times[record.key] = record.t1, record.t2
            if self._selected_record is not None:
                if record.key == self._selected_record[0].key:
                    selected_record = record
            pos = self._determine_record_preferred_pos(
                record, t1, y0, y1, y2, npixels, nsecs
            )
            positions_map[record.key] = pos

        # Organise position objects in a list, and initialize each as a cluster
        positions = positions_map.values()
        positions.sort(key=lambda r: r.pref)
        clusters = []
        for pos in positions:
            if pos.visible:
                clusters.push([pos])

        # Iteratively merge clusters
        distance = 40 + 8
        for iter in range(5):  # while-loop with max 5 iters, just in case

            # Try merging clusters if they're close. Do this from back to front,
            # so we can merge multiple together in one pass
            merged_a_cluster = False
            for i in range(len(clusters) - 2, -1, -1):
                pos1 = clusters[i][-1]
                pos2 = clusters[i + 1][0]
                if pos2.y - pos1.y < distance:
                    merged_a_cluster = True
                    cluster = []
                    cluster.extend(clusters.pop(i))
                    cluster.extend(clusters.pop(i))
                    clusters.insert(i, cluster)
            # If no clusters merged, we're done
            if merged_a_cluster is False:
                break
            # Reposition the elements in each cluster. The strategy for setting
            # positions depends on whether the cluster is near the top/bottom.
            for cluster in clusters:
                if cluster[0].visible == "top":
                    ref_y = cluster[0].y
                    for i, pos in enumerate(cluster):
                        pos.y = ref_y + i * distance
                elif cluster[-1].visible == "bottom":
                    ref_y = cluster[-1].y - (len(cluster) - 1) * distance
                    for i, pos in enumerate(cluster):
                        pos.y = ref_y + i * distance
                else:
                    # Get reference y
                    ref_y = 0.5 * (cluster[0].pref + cluster[-1].pref)
                    # We might still push records over the edge, prevent this
                    first_y = ref_y + (0 + 0.5 - len(cluster) / 2) * distance
                    last_y = ref_y + (len(cluster) - 0.5 - len(cluster) / 2) * distance
                    if first_y < y1 + 20:
                        ref_y += (y1 + 20) - first_y
                    elif last_y > y2 - 20:
                        ref_y -= last_y - (y2 - 20)
                    # Set positions
                    for i, pos in enumerate(cluster):
                        pos.y = ref_y + (i + 0.5 - len(cluster) / 2) * distance

        # Draw records
        for record in records:
            pos = positions_map[record.key]
            self._draw_one_record(
                ctx, record, t1, x1, x2, x3, y0, y1, y2, npixels, nsecs, pos.y
            )

        # Draw the selected record, again, and with extra stuff to allow
        # manipulating it. This is mostly for the timeline
        # representation. Though we also re-draw the representation
        # next to the timeline to make its shadow thicker :)
        if selected_record is not None:
            record = selected_record
            pos = positions_map[record.key]
            self._draw_one_record(
                ctx, record, t1, x1, x2, x3, y0, y1, y2, npixels, nsecs, pos.y
            )
            self._draw_selected_record_extras(
                ctx, record, t1, x1, x2, x3, y0, y1, y2, npixels, nsecs
            )

    def _determine_record_preferred_pos(self, record, t1, y0, y1, y2, npixels, nsecs):
        PSCRIPT_OVERLOAD = False  # noqa
        now = self._canvas.now()
        t2_or_now = now if (record.t1 == record.t2) else record.t2

        # Get position of record in timeline
        ry1 = y0 + npixels * (record.t1 - t1) / nsecs
        ry2 = y0 + npixels * (t2_or_now - t1) / nsecs

        # Determine preferred position
        pref = y = (ry1 + ry2) / 2
        visible = "main"
        if y < y1 + 20:
            y = y1 + 20
            visible = "top"
            if ry2 < y1:
                # Start claiming space before it is visible
                y -= 2 * (y1 - ry2)
                if ry2 < y1 - 40:
                    visible = ""
        elif y > y2 - 20:
            y = y2 - 20
            visible = "bottom"
            if ry1 > y2:
                # Start claiming space before it is visible
                y += 2 * (ry1 - y2)
                if ry1 > y2 + 40:
                    visible = ""

        return {"pref": pref, "y": y, "visible": visible}

    def _draw_one_record(
        self, ctx, record, t1, x1, x4, x6, y0, y1, y2, npixels, nsecs, yy
    ):
        PSCRIPT_OVERLOAD = False  # noqa
        grid_round = self._canvas.grid_round
        now = self._canvas.now()
        t2_or_now = now if (record.t1 == record.t2) else record.t2

        # Define all x's
        #
        #
        #     x1 x2  x3 x4   x5                   x6
        #                     ____________________     ty1
        # ry1  |  ____  |    /                    \
        #      | /    \ |    \____________________/
        #      | |    | |                              ty2
        #      | |    | |
        #      | \____/ |
        # ry2  |        |

        x2 = x1 + 8
        x3 = x4
        x5 = x4 + 25

        # Set record description y positions
        ty1 = yy - 20
        ty2 = yy + 20

        # Get tag info, and determine if this record is selected in the overview
        tags, ds_parts = utils.get_tags_and_parts_from_string(record.ds)
        if len(tags) == 0:
            tags = ["#untagged"]
        tags_selected = True
        selected_tags = self._canvas.widgets.AnalyticsWidget.selected_tags
        if len(selected_tags):
            if not all([tag in tags for tag in selected_tags]):
                tags_selected = False

        # # Determine wheter this record is selected in the timeline
        # selected_in_timeline = False
        # if self._selected_record is not None:
        #     if record.key == self._selected_record[0].key:
        #         selected_in_timeline = True

        # Get position in pixels
        ry1 = y0 + npixels * (record.t1 - t1) / nsecs
        ry2 = y0 + npixels * (t2_or_now - t1) / nsecs
        if ry1 > ry2:
            ry1, ry2 = ry2, ry1  # started timer, then changed time offset
        # Round to pixels? Not during interaction to avoid jumps!
        if self._round_top_bottom:
            ry1 = grid_round(ry1)
            ry2 = grid_round(ry2)

        # Define roundness and how much each slab moves outward
        rn = RECORD_ROUNDNESS
        rnb = COLORBAND_ROUNDNESS
        rne = min(min(0.5 * (ry2 - ry1), rn), rnb)  # for in timeline

        timeline_only = ry2 < y1 or ry1 > y2

        # Draw record representation
        path = utils.RoundedPath()
        if timeline_only:
            path.addVertex(x2, ry2, rne)
            path.addVertex(x2, ry1, rne)
            path.addVertex(x3, ry1, rne)
            path.addVertex(x3, ry2, rne)
        else:
            path.addVertex(x2, ry2, rne)
            path.addVertex(x2, ry1, rne)
            path.addVertex(x4, ry1, 4)
            path.addVertex(x5, ty1, 4)
            path.addVertex(x6, ty1, rn)
            path.addVertex(x6, ty2, rn)
            path.addVertex(x5, ty2, 4)
            path.addVertex(x4, ry2, 4)
        path = path.toPath2D()
        ctx.fillStyle = COLORS.record_bg
        ctx.fill(path)

        ctx.strokeStyle = COLORS.record_edge
        ctx.lineWidth = 1.2

        # Draw coloured edge
        tagz = tags.join(" ")
        tagz = self._canvas.widgets.AnalyticsWidget.tagzmap.get(tagz, tagz)
        colors = [
            window.store.settings.get_color_for_tag(tag) for tag in tagz.split(" ")
        ]
        # Width and xpos
        ew = 8 / len(colors) ** 0.5
        ew = max(ew, rnb)
        ex = x2
        # First band
        ctx.fillStyle = colors[0]
        ctx.beginPath()
        ctx.arc(x2 + rne, ry2 - rne, rne, 0.5 * PI, 1.0 * PI)
        ctx.arc(x2 + rne, ry1 + rne, rne, 1.0 * PI, 1.5 * PI)
        ctx.lineTo(x2 + ew, ry1)
        ctx.lineTo(x2 + ew, ry2)
        ctx.closePath()
        ctx.fill()
        # Remaining bands
        for color in colors[1:]:
            ex += ew  # + 0.15  # small offset creates subtle band
            ctx.fillStyle = color
            ctx.fillRect(ex, ry1, ew, ry2 - ry1)

        # Set back bg color, and draw the record edge
        ctx.fillStyle = COLORS.record_bg
        ctx.stroke(path)

        # Running records have a small outset
        inset, outset = 0, 0
        if record.t1 == record.t2:
            x1f, x2f = x2 + (x3 - x2) / 3, x3 - (x3 - x2) / 3
            inset, outset = 0, 16
            ctx.beginPath()
            ctx.moveTo(x2f, ry2 - inset)
            ctx.arc(x2f - rn, ry2 + outset - rn, rn, 0.0 * PI, 0.5 * PI)
            ctx.arc(x1f + rn, ry2 + outset - rn, rn, 0.5 * PI, 1.0 * PI)
            ctx.lineTo(x1f, ry2 - inset)
            ctx.fill()
            ctx.stroke()
            if int(now) % 2 == 1:
                ctx.fillStyle = COLORS.prim1_clr
                ctx.beginPath()
                ctx.arc(0.5 * (x2 + x3), ry2 + outset / 2, 4, 0, 2 * PI)
                ctx.fill()
            self._picker.register(
                x1f,
                ry2,
                x2f,
                ry2 + outset,
                {"recordrect": True, "region": 0, "record": record},
            )

        # The marker that indicates whether the record has been modified
        if record.st == 0:
            ctx.textAlign = "center"
            ctx.fillStyle = COLORS.record_edge
            ctx.fillText("+", 0.5 * (x2 + x3), 0.5 * (ry1 + ry2))

        # Make the timeline-part clickable - the pick region is increased if needed
        ry1_, ry2_ = ry1, ry2
        if ry2 - ry1 < 16:
            ry1_, ry2_ = 0.5 * (ry1 + ry2) - 8, 0.5 * (ry1 + ry2) + 8
        self._picker.register(
            x2, ry1_, x3, ry2_, {"recordrect": True, "region": 0, "record": record}
        )

        tt_text = tags.join(" ") + "\n(click to make draggable)"
        self._canvas.register_tooltip(x2, ry1, x3, ry2 + outset, tt_text, "mouse")

        # The rest is for the description part
        if timeline_only:
            return

        text_ypos = ty1 + 0.55 * (ty2 - ty1)

        ctx.font = (SMALLER * FONT.size) + "px " + FONT.default
        ctx.textBaseline = "middle"
        faded_clr = COLORS.prim2_clr

        # Draw duration text
        duration = record.t2 - record.t1
        if duration > 0:
            duration_text = dt.duration_string(duration, False)
            duration_sec = ""
        else:
            duration = now - record.t1
            duration_text_full = dt.duration_string(duration, True)
            duration_text, _, duration_sec = duration_text_full.rpartition(":")
            duration_sec = ":" + duration_sec
        ctx.fillStyle = COLORS.record_text if tags_selected else faded_clr
        ctx.textAlign = "right"
        ctx.fillText(duration_text, x5 + 30, text_ypos)
        if duration_sec:
            ctx.fillStyle = faded_clr
            ctx.textAlign = "left"
            ctx.fillText(duration_sec, x5 + 30 + 1, text_ypos)

        # Show desciption
        ctx.font = (SMALLER * FONT.size) + "px " + FONT.default
        ctx.textAlign = "left"
        max_x = x6 - 4
        space_width = ctx.measureText(" ").width + 2
        x = x5 + 55
        ctx.fillStyle = COLORS.record_text if tags_selected else faded_clr
        for part in ds_parts:
            if part.startswith("#"):
                texts = [part]
            else:
                texts = part.split(" ")
            for text in texts:
                if len(text) == 0:
                    continue
                if x > max_x:
                    continue
                new_x = x + ctx.measureText(text).width + space_width
                if new_x <= max_x:
                    if tags_selected and text.startswith("#"):
                        draw_tag(ctx, text, x, text_ypos)
                    else:
                        ctx.fillText(text, x, text_ypos, max_x - x)
                else:
                    ctx.fillText("…", x, text_ypos, max_x - x)
                x = new_x

        # Make description part clickable - the pick region is increased if needed
        d = {
            "button": True,
            "action": "editrecord",
            "help": "",
            "key": record.key,
        }
        self._picker.register(x5, ty1, x6, ty2, d)
        tt_text = tags.join(" ") + "\n(Click to edit)"
        self._canvas.register_tooltip(x5, ty1, x6, ty2, tt_text)

    def _draw_selected_record_extras(
        self, ctx, record, t1, x1, x4, x6, y0, y1, y2, npixels, nsecs, yy
    ):
        PSCRIPT_OVERLOAD = False  # noqa

        grid_round = self._canvas.grid_round

        # Add another x
        x2 = x1 + 8
        x3 = x4
        x5 = x4 + 25  # noqa

        # Get position in pixels
        ry1 = y0 + npixels * (record.t1 - t1) / nsecs
        ry2 = y0 + npixels * (record.t2 - t1) / nsecs
        if record.t1 == record.t2:
            ry2 = y0 + npixels * (self._canvas.now() - t1) / nsecs
        ry1 = grid_round(ry1)
        ry2 = grid_round(ry2)

        # Prepare for drawing
        ctx.lineWidth = 1
        ctx.textBaseline = "middle"
        ctx.textAlign = "center"
        ctx.font = (0.85 * FONT.size) + "px " + FONT.condensed

        # Prepare for drawing flaps
        inset = min(28, max(1, (ry2 - ry1) ** 0.5))
        outset = 30 - inset  # inset + outset = grab height
        rn = grid_round(RECORD_ROUNDNESS)

        shadow_inset = 8
        x1f, x2f = x2 + rn, x3 - rn

        # Disable tooltip at the flaps
        self._canvas.register_tooltip(x1f, ry1 - outset - 1, x2f, ry1 + inset + 1, None)
        self._canvas.register_tooltip(x1f, ry2 - inset - 1, x2f, ry2 + outset + 1, None)

        # The record itself can be used to drag whole thing - if not running
        if record.t1 < record.t2:
            ob = {"recordrect": True, "region": 3, "record": record}
            self._picker.register(x2, ry1, x3, ry2, ob)

        # Flap above to drag t1 - always present
        if True:
            # Picking
            ob = {"recordrect": True, "region": 1, "record": record}
            self._picker.register(x1f, ry1 - outset - 1, x2f, ry1 + inset + 1, ob)
            # Draw flap
            ctx.beginPath()
            ctx.moveTo(x1f, ry1 + inset)
            ctx.arc(x1f + rn, ry1 - outset + rn, rn, 1.0 * PI, 1.5 * PI)
            ctx.arc(x2f - rn, ry1 - outset + rn, rn, 1.5 * PI, 2.0 * PI)
            ctx.lineTo(x2f, ry1 + inset)
            ctx.fillStyle = COLORS.record_bg
            ctx.fill()
            ctx.strokeStyle = COLORS.record_edge
            ctx.stroke()
            # Shadow line
            ctx.beginPath()
            for y in [ry1 + inset]:
                ctx.moveTo(x1f + shadow_inset, y)
                ctx.lineTo(x2f - shadow_inset, y)
            ctx.strokeStyle = COLORS.record_edge
            ctx.stroke()
            # Text
            timetext = dt.time2localstr(record.t1)[11:16]
            ctx.fillStyle = COLORS.record_text
            ctx.fillText(timetext, 0.5 * (x1f + x2f), ry1 + (inset - outset) / 2)

        # Flat below to drag t2 - only present if not running
        if record.t1 < record.t2:
            # Picking
            ob = {"recordrect": True, "region": 2, "record": record}
            self._picker.register(x1f, ry2 - inset - 1, x2f, ry2 + outset + 1, ob)
            # Draw flap
            ctx.beginPath()
            ctx.moveTo(x2f, ry2 - inset)
            ctx.arc(x2f - rn, ry2 + outset - rn, rn, 0.0 * PI, 0.5 * PI)
            ctx.arc(x1f + rn, ry2 + outset - rn, rn, 0.5 * PI, 1.0 * PI)
            ctx.lineTo(x1f, ry2 - inset)
            ctx.fillStyle = COLORS.record_bg
            ctx.fill()
            ctx.strokeStyle = COLORS.record_edge
            ctx.stroke()
            # Shadow line
            ctx.beginPath()
            for y in [ry2 - inset]:
                ctx.moveTo(x1f + shadow_inset, y)
                ctx.lineTo(x2f - shadow_inset, y)
            ctx.strokeStyle = COLORS.record_edge
            ctx.stroke()
            # Text
            timetext = dt.time2localstr(record.t2)[11:16]
            ctx.fillStyle = COLORS.record_text
            ctx.fillText(timetext, 0.5 * (x1f + x2f), ry2 + (outset - inset) / 2)

        # Draw durarion on top
        if False:  # (ry2 - ry1) / 3 > 12:
            duration = record.t2 - record.t1
            duration = duration if duration > 0 else (self._canvas.now() - record.t1)
            if x2 - x1 < 90:
                duration_text = dt.duration_string(duration, False)
                ctx.fillText(duration_text, 0.5 * (x1 + 18 + x2), 0.5 * (ry1 + ry2))
            else:
                duration_text = dt.duration_string(duration, True)
                ctx.fillText(duration_text, 0.5 * (x1 + x2), 0.5 * (ry1 + ry2))

    def _draw_stats(self, ctx, t1, t2, x1, y1, x2, y2, stat_period):

        # Determine header for this block
        t = 0.5 * (t1 + t2)
        if stat_period == "1Y":
            text = str(dt.get_year_month_day(t)[0])
        elif stat_period == "3M":
            quarters = "Q1 Q1 Q1 Q2 Q2 Q2 Q3 Q3 Q3 Q4 Q4 Q4 Q4".split(" ")
            month_index = dt.get_year_month_day(t)[1] - 1
            text = quarters[month_index]  # defensive programming
        elif stat_period == "1M":
            text = dt.get_month_shortname(t)
        elif stat_period == "1W":
            i = dt.get_weeknumber(t)
            text = f"W{i:02.0f}"
        elif stat_period == "1D":
            text = dt.get_weekday_shortname(t)
        else:
            text = ""

        # Get stats for the given time range
        stats_dict = window.store.records.get_stats(t1, t2)
        selected_tags = self._canvas.widgets.AnalyticsWidget.selected_tags

        # Collect per-tag. Also filter selected.
        tag_stats = {}
        sumcount_full = 0
        sumcount_nominal = 0
        sumcount_selected = 0
        for tagz, count in stats_dict.items():
            tags = tagz.split(" ")
            sumcount_full += count * len(tags)
            sumcount_nominal += count
            if len(selected_tags):
                if not all([tag in tags for tag in selected_tags]):
                    continue
            sumcount_selected += count
            for tag in tags:
                tag_stats[tag] = tag_stats.get(tag, 0) + count

        # Turn stats into tuples and sort.
        stats_list = [(tag, count) for tag, count in tag_stats.items()]
        stats_list.sort(key=lambda x: -x[1])

        # Calculate dimensions
        fullwidth = x2 - x1  # * (sumcount_full / (t2 - t1)) # ** 0.5
        fullheight = (y2 - y1) * (sumcount_full / (t2 - t1))  # ** 0.5

        # Show amount of time spend on each tag
        x = x1
        for i in range(len(stats_list)):
            tag, count = stats_list[i]
            width = fullwidth * count / sumcount_full
            ctx.fillStyle = window.store.settings.get_color_for_tag(tag)
            ctx.fillRect(x, y1, width, (y2 - y1))
            x += width  # Next

        # Desaturate the colors by overlaying a semitransparent rectangle.
        # Actually, we use two, as an indicator for the total spent time.
        ctx.fillStyle = COLORS.background1.replace("1)", "0.7)")
        ctx.fillRect(x1, y1, fullwidth, y2 - y1)
        ctx.fillStyle = COLORS.background1.replace("1)", "0.5)")
        ctx.fillRect(x1, y1 + fullheight, fullwidth, y2 - y1 - fullheight)

        bigfontsize = min(FONT.size * 2, (y2 - y1) / 3)
        bigfontsize = max(FONT.size, bigfontsize)
        ymargin = (y2 - y1) / 20

        # Draw big text in blue if it is the timerange containing today
        if t1 < self._canvas.now() < t2:
            ctx.fillStyle = COLORS.prim1_clr
        else:
            ctx.fillStyle = COLORS.prim2_clr

        # Draw duration at the left
        fontsizeleft = bigfontsize * (0.7 if selected_tags else 0.9)
        ctx.font = f"{fontsizeleft}px {FONT.default}"
        ctx.textBaseline = "bottom"
        ctx.textAlign = "left"
        duration_text = dt.duration_string(sumcount_selected, False)
        if selected_tags:
            duration_text += " / " + dt.duration_string(sumcount_nominal, False)
        ctx.fillText(duration_text, x1 + 10, y2 - ymargin)

        # Draw time-range indication at the right
        ctx.font = f"bold {bigfontsize}px {FONT.default}"
        ctx.textBaseline = "bottom"
        ctx.textAlign = "right"
        ctx.fillText(text, x2 - 10, y2 - ymargin)

    def on_wheel(self, ev):
        """Handle wheel event.
        Trackpads usually have buildin inertia (by the OS), so it makese sense
        to use precise scrolling. For mouse wheel, the usual scroll amount
        is 48 units. Throttling breaks the trackpad inertia. But makes scaling
        a bit sensitive, so we do throttle scaling.
        """
        if len(ev.modifiers) == 0 and ev.vscroll != 0:
            self._scroll_trans(ev, ev.vscroll)
        elif len(ev.modifiers) == 0 and ev.hscroll != 0:
            self._scroll_scale(ev, ev.hscroll)
        elif len(ev.modifiers) == 1 and ev.modifiers[0] == "Shift":
            self._scroll_scale(ev, ev.vscroll)
        return True

    def _scroll_trans(self, ev, direction):
        # Get current range and step
        t1, t2 = self._canvas.range.get_range()
        tt1, tt2 = self._canvas.range.get_target_range()
        nsecs_step, nsecs_total = self._canvas.range.get_snap_seconds(0)
        # Apply
        step = 0.15 * nsecs_total * direction / 48
        self._canvas.range.set_range((t1 + tt1) / 2, (t2 + tt2) / 2)
        self._last_trans_scroll = time()
        self._canvas.range.animate_range(tt1 + step, tt2 + step)

    def _scroll_scale(self, ev, direction):
        # Throttle scrolling in scale
        if abs(direction) < 20 or time() - self._last_scale_scroll < 0.6:
            return
        self._last_scale_scroll = time()
        # Select reference pos and time - implicit throttle by not using target_range
        y = (ev.pos[1] - self.rect[1]) / (self.rect[3] - self.rect[1])
        t1, t2 = self._canvas.range.get_range()
        nsecs_before = t2 - t1
        # Determine scaling
        nsecs_step, nsecs_after = self._canvas.range.get_snap_seconds(
            -1 if direction < 0 else 1
        )
        # Apply
        t1 = t1 + (y * nsecs_before - y * nsecs_after)
        t2 = t1 + nsecs_after
        self._canvas.range.animate_range(t1, t2)

    def _pointer_interaction_reset(self):
        self._pointer_startrange = self._canvas.range.get_range()
        for key, pos in self._pointer_pos.items():
            self._pointer_startpos[key] = pos

    def on_pointer_outside(self, ev):
        if self._selected_record is not None:
            self._selected_record = None
            self.update()

    def _selected_record_updated(self):
        if self._selected_record is not None:
            record = self._selected_record[0]
            record = window.store.records.get_by_key(record.key)
            self._selected_record = record, 0, self._canvas.now()
        self.update()

    def on_pointer(self, ev):
        """Determine what kind of interaction mode we're in, and then dispatch
        to either navigation handling or record interaction handling.
        """
        PSCRIPT_OVERLOAD = False  # noqa

        x, y = ev.pos[0], ev.pos[1]

        # Get range in time and pixels
        t1, t2 = self._canvas.range.get_range()
        _, y1, _, y2 = self.rect
        npixels = y2 - y1
        nsecs = t2 - t1

        # Get current pos
        t = t1 + (y - y1) * nsecs / npixels

        # Determine when to transition from one mode to another
        last_interaction_mode = self._interaction_mode
        if "down" in ev.type:
            if self._interaction_mode == 0 and ev.ntouches == 1:
                self._interaction_mode = 1  # mode undecided
                self._last_pointer_down_event = ev
                self.update()
            else:  # multi-touch -> tick-widget-behavior-mode
                self._interaction_mode = 2
        elif "move" in ev.type:
            if self._interaction_mode == 1:
                downx, downy = self._last_pointer_down_event.pos
                if Math.sqrt((x - downx) ** 2 + (y - downy) ** 2) > 10:
                    self._interaction_mode = 2  # tick-widget-behavior-mode
        elif "up" in ev.type:
            if "mouse" in ev.type or ev.ntouches == 0:
                self._interaction_mode = 0

        # Things that trigger on a pointer down if we have not entered tick-behavior-mode yet.
        # These are starts of a drag operation not related to timeline navigation.
        if self._interaction_mode != 2 and "down" in ev.type:
            picked = self._picker.pick(x, y)
            if picked is not None:
                if picked.recordrect and picked.region:
                    # Initiate record drag
                    self._selected_record = [picked.record, picked.region, t]
                    self._interaction_mode = 0
                    self.update()
                    return

        # Things that only trigger if we did not move the mouse too much
        if last_interaction_mode == 1 and "up" in ev.type:
            picked = self._picker.pick(x, y)
            if picked is not None:
                if picked.statrect:
                    # A stat rectangle
                    self._canvas.range.animate_range(picked.t1, picked.t2)
                elif picked.recordrect and not picked.region:
                    # Select a record
                    self._selected_record = [picked.record, 0, t]
                elif picked.button is True:
                    # A button was pressed
                    self._handle_button_press(picked.action, picked)
                self.update()
                return

        # Dispatch to navigation handler?
        if last_interaction_mode == 2 or self._interaction_mode == 2:
            if self._last_pointer_down_event is not None:
                self.on_pointer_navigate(self._last_pointer_down_event)
                self._last_pointer_down_event = None
            self.on_pointer_navigate(ev)

        # Dispatch to record interaction?
        if self._interaction_mode == 0:
            if self._can_interact_with_records is False:
                pass  # self._selected_record = None
            else:
                self._on_pointer_handle_record_interaction(ev)

    def _on_pointer_handle_record_interaction(self, ev):
        PSCRIPT_OVERLOAD = False  # noqa

        y = ev.pos[1]

        # Get range in time and pixels
        t1, t2 = self._canvas.range.get_range()
        _, y1, _, y2 = self.rect
        npixels = y2 - y1
        nsecs = t2 - t1

        # Get current pos
        t = t1 + (y - y1) * nsecs / npixels
        tround = 1
        secspernpixels = 10 * nsecs / npixels
        if secspernpixels > 100:
            tround = 300  # 5 min
        elif secspernpixels > 60:
            tround = 60  # 1 min

        def snap_t1(record):
            PSCRIPT_OVERLOAD = False  # noqa
            for key in self._record_times.keys():
                if key == record.key:
                    continue
                t1, t2 = self._record_times[key]
                if t2 - 2.5 * secspernpixels <= record.t1 <= t2 + tround * 0.5:
                    record.t1 = t2
                    return True
            else:
                record.t1 = Math.round(record.t1 / tround) * tround

        def snap_t2(record):
            PSCRIPT_OVERLOAD = False  # noqa
            for key in self._record_times.keys():
                if key == record.key:
                    continue
                t1, t2 = self._record_times[key]
                if t1 - tround * 0.5 <= record.t2 <= t1 + 2.5 * secspernpixels:
                    record.t2 = t1
                    return True
            else:
                record.t2 = Math.round(record.t2 / tround) * tround

        # Dragging the selected record
        if self._selected_record is not None:
            if "move" in ev.type or "up" in ev.type:
                if self._selected_record[1] > 0:
                    # Prepare
                    tstart = self._selected_record[2]
                    tdelta = t - tstart  # how much we have moved
                    record = self._selected_record[0].copy()
                    isrunning = record.t1 == record.t2
                    if isrunning:
                        record.t2 = self._canvas.now()
                    # Move
                    if self._selected_record[1] == 1 or self._selected_record[1] == 3:
                        record.t1 += tdelta
                    if self._selected_record[1] == 2 or self._selected_record[1] == 3:
                        record.t2 += tdelta
                    # Snap
                    if self._selected_record[1] == 1:
                        snap_t1(record)
                    elif self._selected_record[1] == 2:
                        snap_t2(record)
                    elif self._selected_record[1] == 3:
                        dt = record.t2 - record.t1
                        if not snap_t1(record) and snap_t2(record):
                            record.t1 = record.t2 - dt
                        else:
                            record.t2 = record.t1 + dt
                    # Finish
                    if self._selected_record[1] == 1:
                        record.t1 = min(record.t2 - 10, record.t1)
                    else:
                        record.t2 = max(record.t1 + 10, record.t2)
                    if isrunning:
                        record.t1 = min(record.t1, self._canvas.now())
                        record.t2 = record.t1
                    window.store.records.put(record)
                    if "up" in ev.type:
                        self._selected_record[1] = 0
                    self.update()
                elif "up" in ev.type:  # -> self._selected_record[1] == 0:
                    # Disable when clicking elsewhere
                    self._selected_record = None
                    self.update()

    def on_pointer_navigate(self, ev):
        """Handle mouse or touch event for navigation."""
        PSCRIPT_OVERLOAD = False  # noqa

        y = ev.pos[1]

        if "down" in ev.type:
            self._pointer_inertia = []
            for key, pos in ev.touches.items():
                self._pointer_pos[key] = pos
            self._pointer_interaction_reset()
            self.update()  # with mouse down, header is different
        elif len(self._pointer_pos.keys()) == 0:
            return
        elif "mouse_move" == ev.type:  # MOUSE
            key = ev.touches.keys()[0]
            if 1 in ev.buttons:  # also if 2 is *also* down
                # Determine how much "time" the pointer has moved
                t1, t2 = self._pointer_startrange
                dy = self._pointer_startpos[key][1] - y
                nsecs = t2 - t1
                npixels = self.rect[3] - 30 - 5
                dsecs = nsecs * dy / npixels  # relative to start pos
                # Inertia
                self._pointer_inertia.push((dsecs, perf_counter()))
                while len(self._pointer_inertia) > 10:
                    self._pointer_inertia.pop(0)
                # Set it, and set new ref
                self._canvas.range.set_range(t1 + dsecs, t2 + dsecs)
                self._pointer_pos[key] = ev.pos
            elif 2 in ev.buttons:
                # Select reference position and time
                _, y1, _, y2 = self.rect
                ref_y = (self._pointer_startpos[key][1] - y1) / (y2 - y1)
                t1, t2 = self._pointer_startrange
                nsecs_before = t2 - t1
                # Determine scaling
                factor = 4
                dy = self._pointer_startpos[key][1] - y
                npixels = self.rect[3] - 30 - 5
                nsecs_after = nsecs_before * 2 ** (factor * dy / npixels)
                # Apply
                t1 = t1 + ref_y * (nsecs_before - nsecs_after)
                t2 = t1 + nsecs_after
                self._canvas.range.set_range(t1, t2)
                self._pointer_pos[key] = ev.pos
        elif "touch_move" == ev.type:  # TOUCH
            for key, pos in ev.touches.items():
                if key in self._pointer_pos:
                    self._pointer_pos[key] = pos
            # Calculate avg position and spread
            avg_pos1, std_pos1 = utils.positions_mean_and_std(
                self._pointer_startpos.values()
            )
            avg_pos2, std_pos2 = utils.positions_mean_and_std(
                self._pointer_pos.values()
            )
            # Calculate how to change the range
            t1, t2 = self._pointer_startrange
            nsecs_before = nsecs_after = t2 - t1
            npixels = self.rect[3] - 30 - 5
            if len(self._pointer_pos.keys()) > 1:
                factor = 9
                dy = std_pos1[1] - std_pos2[1]
                nsecs_after = nsecs_before * 2 ** (factor * dy / npixels)
            if True:
                dy = avg_pos1[1] - avg_pos2[1]
                dsecs = nsecs_after * dy / npixels
                # Inertia
                self._pointer_inertia.push((dsecs, perf_counter()))
                while len(self._pointer_inertia) > 10:
                    self._pointer_inertia.pop(0)
            # Apply
            mo_seconds = nsecs_after - nsecs_before
            t1 -= 0.5 * mo_seconds
            t2 += 0.5 * mo_seconds
            self._canvas.range.set_range(t1 + dsecs, t2 + dsecs)
        elif "up" in ev.type:
            for key in ev.touches.keys():
                self._pointer_pos.pop(key)
                self._pointer_startpos.pop(key)
            if len(self._pointer_pos.keys()) > 0:
                self._pointer_interaction_reset()
            else:
                # Finish the interaction - maybe apply inertia
                t1_begin, t2_begin = self._pointer_startrange
                t1_end, t2_end = self._canvas.range.get_range()
                already_panned = 0.5 * (t1_end + t2_end) - 0.5 * (t1_begin + t2_begin)
                if len(self._pointer_inertia) > 1:
                    for i in range(2, len(self._pointer_inertia) + 1):
                        ddsec = (
                            self._pointer_inertia[-1][0] - self._pointer_inertia[-i][0]
                        )
                        dtime = (
                            self._pointer_inertia[-1][1] - self._pointer_inertia[-i][1]
                        )
                        if dtime > 0.4:
                            break
                        if dtime > 0.02:
                            dsecs = 0.5 * ddsec / dtime
                            if already_panned > 0:
                                dsecs = min(dsecs, already_panned)
                            else:
                                dsecs = max(dsecs, already_panned)
                            t1, t2 = self._canvas.range.get_target_range()
                            self._canvas.range.animate_range(t1 + dsecs, t2 + dsecs)
                            return
                # If no inertia, snap
                self._canvas.range.snap()
                self.update()

    def _handle_button_press(self, action, picked):
        now = self._canvas.now()
        if action == "showrecords":
            self._canvas._prefer_show_analytics = False
            self._canvas.on_resize()
            self.update()
        elif action.startswith("zoom_"):
            t1, t2 = self._canvas.range.get_target_range()
            res = action.split("_")[-1]
            now_is_in_range = t1 <= now <= t2
            if res == "-1" or res == "+1":
                if res == "-1":
                    t1, t2 = self._canvas.range.get_snap_range(-1)
                else:
                    t1, t2 = self._canvas.range.get_snap_range(+1)
                if now_is_in_range:
                    t1, t2 = now - 0.5 * (t2 - t1), now + 0.5 * (t2 - t1)
            else:
                t_ref = now if (t1 <= now <= t2) else (t2 + t1) / 2
                t1 = dt.floor(t_ref, res)
                t2 = dt.add(t1, res)
            self._canvas.range.animate_range(t1, t2)
        elif action.startswith("step_"):
            t1, t2 = self._canvas.range.get_target_range()
            nsecs = t2 - t1
            if action == "step_backward":
                self._canvas.range.animate_range(t1 - nsecs, t1)
            else:
                self._canvas.range.animate_range(t2, t2 + nsecs)
        elif action == "editrecord":
            record = window.store.records.get_by_key(picked.key)
            self._canvas.record_dialog.open(
                "Edit", record, self._selected_record_updated
            )
        elif action == "editcurrentrecord":
            # The button for the currently selected record
            if self._selected_record:
                record = self._selected_record[0]  # before-drag!
                record = window.store.records.get_by_key(record.key)
                self._canvas.record_dialog.open(
                    "Edit", record, self._selected_record_updated
                )


class AnalyticsWidget(Widget):
    """Widget that draws the analytics, and handles corresponding interaction."""

    def on_init(self):
        self._picker = utils.Picker()
        self.selected_tags = []
        self._need_more_drawing_flag = False
        self._time_at_last_draw = 0
        self._time_since_last_draw = 0
        self._npixels_each = 0
        self.tagzmap = {}  # public map of tagz -> tagz
        # Init tag cache and root
        self._tag_bars = {}  # name -> bar-info
        self._tag_bars[""] = {
            "key": "",
            "tagz": "",
            "subtagz": "",
            "t": 0,
            "cum_t": 0,
            "inset": 0,
            "xoffset": 0,
            "cum_offset": 0,
            "target_inset": 0,
            "height": 0,
            "target_height": 0,
            "subs": [],
        }

    def on_draw(self, ctx):

        x1, y1, x2, y2 = self.rect
        self._picker.clear()

        # If too little space, only draw button to expand
        if x2 - x1 <= 50:
            width = 30
            x3, x4 = self._canvas.w - width, self._canvas.w
            height = max(220, 0.33 * (y2 - y1))
            y3, y4 = (y1 + y2) / 2 - height / 2, (y1 + y2) / 2 + height / 2
            ctx.beginPath()
            ctx.moveTo(x4, y3)
            ctx.lineTo(x3, y3 + width)
            ctx.lineTo(x3, y4 - width)
            ctx.lineTo(x4, y4)
            ctx.fillStyle = COLORS.tick_stripe2
            ctx.fill()
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"
            ctx.fillStyle = COLORS.prim1_clr
            ctx.font = FONT.size + "px " + FONT.default
            for i, c in enumerate("Overview"):
                ctx.fillText(c, (x3 + x4) / 2, (y3 + y4) / 2 + (i - 4) * 18)
            self._picker.register(
                x3, y3, x4, y4, {"button": True, "action": "showanalytics"}
            )
            return

        self._help_text = ""

        # Process _time_at_last_draw, and set _time_since_last_draw
        time_now = time()
        if self._time_since_last_draw > 0:
            self._time_since_last_draw = time_now - self._time_at_last_draw
        else:
            self._time_since_last_draw = 0
        self._time_at_last_draw = time_now

        self._need_more_drawing_flag = False

        self._draw_stats(ctx, x1, y1, x2, y2)

        if self._need_more_drawing_flag:
            self._time_since_last_draw = 1
            self.update()
        else:
            self._time_since_last_draw = 0

        # Draw title text
        if self._canvas.w > 700:
            text1 = "Overview"
            text2 = self._help_text
            ctx.textAlign = "right"
            ctx.textBaseline = "top"
            #
            ctx.font = "bold " + (FONT.size * 1.4) + "px " + FONT.mono
            ctx.fillStyle = COLORS.prim2_clr
            ctx.fillText(text1, x2 - 10, 65)
            #
            ctx.font = (FONT.size * 0.9) + "px " + FONT.default
            ctx.fillStyle = COLORS.prim2_clr
            ctx.fillText(text2, x2 - 10, 90)

        # Show some help if no records are shown
        if len(self._level_counts) == 1:

            ctx.textAlign = "left"
            ctx.font = FONT.size + "px " + FONT.default

            t1, t2 = self._canvas.range.get_range()
            if t1 < self._canvas.now() < t2:
                ctx.textBaseline = "top"
                ctx.fillStyle = COLORS.prim1_clr
                text = "Click the ▶ button to start tracking!"
                ctx.fillText(text, x1 + 5, y1 + self._npixels_each + 25)

    def _draw_stats(self, ctx, x1, y1, x2, y2):
        PSCRIPT_OVERLOAD = False  # noqa

        root = self._tag_bars[""]

        # Reset times for all elements. The one that are still valid
        # will get their time set.
        for key in self._tag_bars.keys():
            self._tag_bars[key].cum_t = 0
            self._tag_bars[key].t = 0

        # Get stats for the current time range
        t1, t2 = self._canvas.range.get_range()
        stats = window.store.records.get_stats(t1, t2)

        # Get per-tag info, for tooltips
        self._time_per_tag = {}
        for tagz, t in stats.items():
            tags = tagz.split(" ")
            for tag in tags:
                self._time_per_tag[tag] = self._time_per_tag.get(tag, 0) + t

        # Get better names (order of tags in each tag combo)
        name_map = utils.get_better_tag_order_from_stats(
            stats, self.selected_tags, False
        )
        self.tagzmap.update(name_map)

        # Replace the stats with the fixed names
        new_stats = {}
        for tagz1, tagz2 in name_map.items():
            new_stats[tagz2] = stats[tagz1]

        # Group tags - creating "indentation"
        group_counts = {}
        if len(self.selected_tags) > 0:
            selected_tagz = self.selected_tags.join(" ")
            for tagz in new_stats.keys():
                tags = tagz.split(" ")
                for level in range(len(tags)):
                    tagz = tags[: level + 1].join(" ")
                    if selected_tagz == tagz:
                        group_counts[tagz] = group_counts.get(tagz, 0) + 1

        # Insert any new tags into the hierarchy
        for tagz, t in new_stats.items():
            tags = tagz.split(" ")
            dprev = root
            key = ""
            for level in range(len(tags)):
                tagz = tags[: level + 1].join(" ")
                is_leaf = level == len(tags) - 1
                # Add an element if this is the leaf, or if the parent is a group
                # with more than 1 member. And if the item is not already present.
                if is_leaf or group_counts.get(tagz, 0) > 0:
                    the_t = t if is_leaf else 0
                    key += "/ " + tagz
                    if key in self._tag_bars:
                        dprev = self._tag_bars[key]
                        dprev.t = the_t
                    else:
                        d = {
                            "key": key,
                            "tagz": tagz,
                            "subtagz": tagz[len(dprev.tagz) :].lstrip(" "),
                            "t": the_t,
                            "cum_t": 0,
                            "inset": 0,
                            "target_inset": 0,
                            "xoffset": 0,
                            "target_xoffset": 0,
                            "height": 0,
                            "target_height": 0,
                            "cum_offset": 0,
                            "subs": [],
                        }
                        dprev.subs.push(d)
                        # dprev.subs.sort(key=lambda x: x.subtagz.lower())
                        # sort_items(dprev.subs)
                        self._tag_bars[key] = d
                        dprev = d

        # # Validating our persistent structure integrity - comment when we're done
        # known_names = window.Set()
        #
        # def collect_names(d):
        #     known_names.add(d.tagz)
        #     for sub in d.subs:
        #         collect_names(sub)
        #
        # collect_names(root)
        # for tagz in self._tag_bars.keys():
        #     assert known_names.has(tagz)

        # First resolve pass: resolve cumulative t, level, is_selected
        self._level_counts = []  # list of [selected_bars, unselected_bars]
        self._resolve_t(root, 0)

        # Determine root inset, based on total time. But asymptotically limit it.
        # This is based on the "softlimit" function.
        one_pixel_in_secs = 30 * 60
        npixels = root.cum_t / one_pixel_in_secs
        avail_inset = 80
        root_target_inset = -avail_inset * (Math.exp(-npixels / avail_inset) - 1)
        root_target_inset *= min(80, ((x2 - x1) / 6)) / 80  # responsive
        npixels_each_min_max = 40, 60

        # Determine max level and derive more props
        avail_height = (y2 - y1) - (avail_inset / 4) * 2
        n_max = avail_height / npixels_each_min_max[0]
        n = 0
        for level in range(len(self._level_counts)):
            n += self._level_counts[level][0]  # selected
        for level in range(len(self._level_counts)):
            n += self._level_counts[level][1]  # unselected
            if n > n_max:
                break
        self._maxlevel = max(1, level - 1)
        if self._maxlevel == 1 and len(self._level_counts) <= 1:
            self._maxlevel = 0

        # Set _npixels_each (number of pixels per bar)
        n = 0
        for level in range(len(self._level_counts)):
            n += self._level_counts[level][0]  # selected
        for level in range(self._maxlevel + 1):
            n += self._level_counts[level][1]  # unselected
        npixels_each = min(avail_height / n, npixels_each_min_max[1])
        self._npixels_each = self._slowly_update_value(self._npixels_each, npixels_each)

        # Three resolve passes: target inset and height, real inset and height, positioning
        self._max_cum_offset = 0
        self._resolve_target_inset_and_height(root, root_target_inset, root.cum_t)
        self._resolve_real_inset_and_height(root, None)
        self._resolve_positions(root, x1, x2 - self._max_cum_offset - 4, y1)

        # Sort bars, so that they are correctly drawn over each-other (assuming ortho projection)
        bars = self._tag_bars.values()
        bars.sort(key=lambda unit: -unit.y1)
        bars.sort(key=lambda unit: unit.level)

        # Prepare for drawing texts
        ctx.textBaseline = "middle"
        ctx.textAlign = "left"

        # Draw all bars
        for bar in bars:
            if bar.height > 0:
                self._draw_one_stat_unit(ctx, bar, root.cum_t)

        # Determine help text
        if self._maxlevel > 0:
            if len(self.selected_tags) == 0:
                self._help_text = "click a tag to filter"
            else:
                self._help_text = "click more tags to filter more"

    def _invalidate_element(self, d, parent=None):
        d.invalid = True
        # parent.subs.remove(d)
        # d.cum_t = 0
        # d.t = 0
        for sub in d.subs:
            self._invalidate_element(sub)
        #     d.subs = []

    def _slowly_update_value(self, current, target):
        PSCRIPT_OVERLOAD = False  # noqa
        delta = target - current
        snap_limit = 1.5  # How close the value must be to just set it
        speed = 0.25  # The fraction of delta to apply. Smooth vs snappy.
        if self._time_since_last_draw > 0:
            speed = min(0.8, 12 * self._time_since_last_draw)
        if abs(delta) > snap_limit:
            self._need_more_drawing_flag = True
            return current + delta * speed
        else:
            return target

    def _resolve_t(self, d, level, parent_is_selected=0):
        """Calculate cumulative t and t percentage for all bars.
        Also set level and is_selected.
        """
        PSCRIPT_OVERLOAD = False  # noqa

        # Set level
        d.level = level
        if len(self._level_counts) <= level:
            self._level_counts.push([0, 0])

        # Get whether this bar (or a parent) is selected
        d.is_selected = 0
        if parent_is_selected:
            d.is_selected = 3
        # elif self.selected_tags and d.tagz == self.selected_tags.join(" "):
        #     d.is_selected = 2

        # Recurse to subs
        cum_t = 0
        sub_is_selected = False
        for sub in d.subs:
            self._resolve_t(sub, level + 1, d.is_selected)
            cum_t += sub.cum_t
            sub_is_selected = sub_is_selected or sub.is_selected

        d.cum_t = cum_t + d.t

        # Apply percentages
        d.percent_t = 1  # default or root
        for sub in d.subs:
            sub.percent_t = sub.cum_t / max(0.001, d.cum_t)

        # Sort the items
        utils.order_stats_by_duration_and_name(d.subs)

        # Set level count now that we know whether we are selected
        if d.is_selected == 0 and sub_is_selected:
            d.is_selected = 1
        if d.is_selected:
            self._level_counts[level][0] += 1
        else:
            self._level_counts[level][1] += 1

    def _resolve_target_inset_and_height(self, d, base_inset, base_cum_t):
        """Calculate target inset and height for all bars."""
        PSCRIPT_OVERLOAD = False  # noqa

        # Set own inset
        d.target_inset = base_inset * d.cum_t / max(0.001, base_cum_t)

        # Set own xoffset
        d.target_xoffset = 10  # max(0, 15 - base_inset)
        if d.level == 0:
            d.target_xoffset = 0
        elif d.is_selected == 2:
            d.target_xoffset -= 10

        # Recurse to subs
        cum_target_height = 0
        cum_target_inset = 0
        for sub in d.subs:
            self._resolve_target_inset_and_height(sub, d.target_inset, d.cum_t)
            cum_target_height += sub.target_height
            cum_target_inset += sub.target_inset

        cum_target_height += self._npixels_each
        cum_target_inset += d.target_inset

        # Set our own target height
        if (
            d.level == 0
            or cum_target_inset > 0
            or d.is_selected == 1
            or d.is_selected == 2
        ):
            d.target_height = cum_target_height
        else:
            d.target_height = 0

        # If this was the last valid level, target zero size, unless selected.
        if d.level == 0:
            d.target_inset = 0
        if d.level > self._maxlevel:
            if not d.is_selected:
                d.target_height = 0
                d.target_inset = 0

    def _resolve_real_inset_and_height(self, d, height_limit=None):
        """Calculate the real height, inset and cum_offset, limiting as needed."""
        PSCRIPT_OVERLOAD = False  # noqa

        # Set actual height, inset, xoffset
        d.height = self._slowly_update_value(d.height, d.target_height)
        d.inset = self._slowly_update_value(d.inset, d.target_inset)
        d.xoffset = self._slowly_update_value(d.xoffset, d.target_xoffset)

        # Set cum_offset for base
        if d.level == 0:
            d.cum_offset = d.inset + d.xoffset

        # Limit height
        if height_limit is not None and d.height > height_limit + 0.1:
            d.height = height_limit

        # Recurse to subs
        height_left = max(0, d.height - self._npixels_each)
        for sub in d.subs:
            self._resolve_real_inset_and_height(sub, height_left)
            height_left = max(0, height_left - sub.height)
            # Set cum inset too
            sub.cum_offset = d.cum_offset + sub.inset + sub.xoffset
            self._max_cum_offset = max(self._max_cum_offset, sub.cum_offset)

        # Delete any subs?
        new_subs = []
        for sub in d.subs:
            if sub.cum_t == 0 and sub.inset == 0 and sub.height == 0:
                self._tag_bars.pop(sub.key)
            else:
                new_subs.push(sub)
        d.subs = new_subs

    def _resolve_positions(self, d, x1, x4, y):
        """Calculate the positions of the bar.
        With x2-x3-y2-y3 the rectangle that forms the base of the bar,
         and x1-x4-y1-y4 the front of the bar.
         Input args x1, x4 represent the base of the parent, and y the vertical pos.
        """
        PSCRIPT_OVERLOAD = False  # noqa

        # Note that it is important to resolve all positions, even if the height is zero,
        # because sub bars may have a nonzero height (?), but more importantly,
        # to get the order of drawing correct.

        inset = 0  # d.inset

        # Set x's
        d.x1 = x1 + d.xoffset
        d.x2 = d.x1 + inset
        d.x4 = x4 + d.xoffset
        d.x3 = d.x4 + inset

        margin = 0

        # Set y's - orthographic projection
        d.y1 = y
        d.y4 = d.y1 + d.height - margin
        d.y2 = d.y1 + inset / 4
        d.y3 = d.y4 + inset / 4

        # Recurse to subs
        y = d.y2 + min(d.height, self._npixels_each)
        for sub in d.subs:
            self._resolve_positions(sub, d.x2, d.x3, y)
            y = sub.y4 + margin

    def _draw_one_stat_unit(self, ctx, unit, totaltime):
        PSCRIPT_OVERLOAD = False  # noqa

        t1, t2 = self._canvas.range.get_range()
        x2, x3 = unit.x2, unit.x3
        y2, y3 = unit.y2, unit.y3

        is_root = unit.level == 0
        target_npixels = self._npixels_each
        npixels = min(y3 - y2, target_npixels)

        if is_root:
            y3 += 8

        # Roundness
        rn = min(ANALYSIS_ROUNDNESS, npixels / 2)
        rnb = min(COLORBAND_ROUNDNESS, npixels / 2)

        # Draw front
        path = window.Path2D()
        path.arc(x3 - rn, y2 + rn, rn, 1.5 * PI, 2.0 * PI)
        path.arc(x3 - rn, y3 - rn, rn, 0.0 * PI, 0.5 * PI)
        path.arc(x2 + rnb, y3 - rnb, rnb, 0.5 * PI, 1.0 * PI)
        path.arc(x2 + rnb, y2 + rnb, rnb, 1.0 * PI, 1.5 * PI)
        path.closePath()
        if is_root:
            ctx.lineWidth = 3
            ctx.strokeStyle = COLORS.panel_edge
            ctx.fillStyle = COLORS.panel_bg
        else:
            ctx.lineWidth = 1.2
            ctx.strokeStyle = COLORS.record_edge
            ctx.fillStyle = COLORS.record_bg
        ctx.fill(path)

        # Draw more, or are we (dis)appearing?
        if unit.height / target_npixels < 0.3:
            ctx.stroke(path)
            return

        ymid = y2 + 0.55 * npixels
        x_ref_duration = x3 - 35  # right side of minute
        x_ref_labels = x2 + 30  # start of labels

        # Draw coloured edge
        if unit.level > 0 and unit.level == self._maxlevel:
            colors = [
                window.store.settings.get_color_for_tag(tag)
                for tag in unit.tagz.split(" ")
            ]
            # Width and xpos
            ew = 8 / len(colors) ** 0.5
            ew = max(ew, rnb)
            ex = x2
            # First band
            ctx.fillStyle = colors[0]
            ctx.beginPath()
            ctx.arc(x2 + rnb, y3 - rnb, rnb, 0.5 * PI, 1.0 * PI)
            ctx.arc(x2 + rnb, y2 + rnb, rnb, 1.0 * PI, 1.5 * PI)
            ctx.lineTo(x2 + ew, y2)
            ctx.lineTo(x2 + ew, y3)
            ctx.closePath()
            ctx.fill()
            # Remaining bands
            for color in colors[1:]:
                ex += ew  # + 0.15  # small offset creates subtle band
                ctx.fillStyle = color
                ctx.fillRect(ex, y2, ew, y3 - y2)
            ex += ew
            # That coloured region is also a button
            self._picker.register(
                x2,
                y2,
                ex,
                y3,
                {"button": True, "action": "chosecolor:" + unit.tagz},
            )
            tt_text = "Color for " + unit.tagz + "\n(Click to change color)"
            self._canvas.register_tooltip(
                x2,
                y2,
                ex,
                y3,
                tt_text,
            )

        # Draw edge
        ctx.stroke(path)

        # Get duration text
        show_secs = False
        if t1 < self._canvas.now() < t2:
            for record in window.store.records.get_running_records():
                if window.store.records.tags_from_record(record).join(" ") == unit.tagz:
                    show_secs = True
        if show_secs:
            duration, _, duration_sec = dt.duration_string(unit.cum_t, True).rpartition(
                ":"
            )
            duration_sec = ":" + duration_sec
        else:
            duration = dt.duration_string(unit.cum_t, False)
            duration_sec = ""

        # Draw text labels
        tx, ty = x_ref_labels, ymid
        ctx.font = FONT.size + "px " + FONT.default
        ctx.fillStyle = COLORS.record_text
        ctx.lineWidth = 1.2
        ctx.strokeStyle = COLORS.acc_clr
        # Define text labels, and draw initial duration
        texts = []
        if is_root:
            if len(self.selected_tags):
                tx = unit.x2 + 11
                texts.push([" ←  back to all ", "select:", "Full overview"])
                if len(self.selected_tags) == 1:
                    action = "chosecolor:" + self.selected_tags[0]
                    texts.push(["fas-\uf53f", action, "Select a diferent color"])
            else:
                ctx.textAlign = "right"
                ctx.fillText(duration, x_ref_duration, ty)
                if unit.cum_t > 0:
                    texts.push(["Total"])
                else:
                    texts.push(["Total"])
        else:
            ctx.textAlign = "right"
            ctx.fillText(duration, x_ref_duration, ty)
            if len(self.selected_tags) and unit.level == 1:
                texts.push(["Total of"])
            if duration_sec:
                ctx.textAlign = "left"
                ctx.fillStyle = COLORS.prim2_clr
                ctx.fillText(duration_sec, x_ref_duration + 1, ty)
            tags = [tag for tag in unit.subtagz.split(" ")]
            for tag in tags:
                if tag in self.selected_tags:
                    texts.push([tag, ""])
                else:
                    tt = dt.duration_string(self._time_per_tag.get(tag, 0))
                    tt += " in total"
                    tt += "\n(Click to filter)"
                    texts.push([tag, "select:" + tag, tt])
        if unit.is_selected >= 2 and unit.cum_t > 0:
            texts.push([f" ({100*unit.percent_t:0.0f}%)", ""])
        # Draw text labels
        ctx.textAlign = "left"
        ctx.font = FONT.size + "px " + FONT.default
        for text, action, tt in texts:
            if action and text.startswith("#"):
                opt = {
                    "ref": "leftmiddle",
                    "color": COLORS.button_text,
                    # "padding": 0,
                }
                dx = self._draw_button(ctx, tx, ty, None, 30, text, action, tt, opt)
                tx += dx + 12
            elif action:
                opt = {"ref": "leftmiddle"}
                dx = self._draw_button(ctx, tx, ty, None, 30, text, action, tt, opt)
                tx += dx + 4
            else:
                ctx.fillStyle = COLORS.record_text
                if text.startsWith("#"):
                    draw_tag(ctx, text, tx, ty)
                else:
                    ctx.fillText(text, tx, ty)
                tx += ctx.measureText(text).width + 12

    def on_pointer(self, ev):

        x, y = ev.pos[0], ev.pos[1]

        if "down" in ev.type:
            picked = self._picker.pick(x, y)
            if picked is None or picked == "":
                pass
            elif picked.button:
                if picked.action == "showanalytics":
                    self._canvas._prefer_show_analytics = True
                    self._canvas.on_resize()
                    self.update()
                elif picked.action == "report":
                    t1, t2 = self._canvas.range.get_range()
                    self._canvas.report_dialog.open(t1, t2, self.selected_tags)
                elif picked.action.startswith("select:"):
                    _, _, tag = picked.action.partition(":")
                    if tag:
                        if tag not in self.selected_tags:
                            self.selected_tags.push(tag)
                    else:
                        self.selected_tags = []
                elif picked.action.startswith("chosecolor:"):
                    _, _, tagz = picked.action.partition(":")
                    tags = tagz.split(" ")
                    if len(tags) == 1:
                        self._canvas.tag_color_dialog.open(tags[0], self.update)
                    elif len(tags) > 1:
                        self._canvas.tag_color_selection_dialog.open(tags, self.update)
                self.update()


if __name__ == "__main__":
    import pscript

    pscript.script2js(
        __file__, target=__file__[:-3] + ".js", namespace="front", module_type="simple"
    )
