"""
Implementation of HTML-based dialogs.
"""

from pscript import this_is_js
from pscript.stubs import window, console, Math, isFinite, Date, isNaN


if this_is_js():
    dt = window.dt
    utils = window.utils

# A stack of dialogs
stack = []


def to_str(x):
    return window.stores.to_str(x)


def show_background_div(show, keep_transparent=False):
    # Create element?
    if not window.dialogbackdiv:
        window.dialogbackdiv = window.document.createElement("div")
        window.dialogbackdiv.className = "dialog-cover"
        document.getElementById("canvas").parentNode.appendChild(window.dialogbackdiv)
        # Make it block events
        evts = "click", "mousedown", "mousemove", "touchstart", "touchmove"
        for evname in evts:
            window.dialogbackdiv.addEventListener(
                evname, handle_background_div_event, 0
            )
        window.addEventListener("blur", handle_window_blur_event)
        # Block key events (on a div that sits in between dialog and window)
        document.getElementById("main-content").addEventListener(
            "keydown", handle_background_div_event, 0
        )

    if show:
        alpha = 0.0 if keep_transparent else 0.2
        window.dialogbackdiv.style.background = f"rgba(0, 0, 0, {alpha})"
        window.dialogbackdiv.style.pointerEvents = "auto"
        window.dialogbackdiv.style.display = "block"
    else:
        # window.dialogbackdiv.style.display = "none"
        window.dialogbackdiv.style.pointerEvents = "none"
        window.dialogbackdiv.style.background = "rgba(255, 0, 0, 0.0)"


def handle_background_div_event(e):
    if window.dialogbackdiv.style.display == "none":
        return
    e.stopPropagation()
    if e.type == "touchstart":
        e.preventDefault()  # prevent browser sending touch events as a "click" later
    if e.type == "mousedown" or e.type == "touchstart":
        if len(stack) > 0:
            if stack[-1].EXIT_ON_CLICK_OUTSIDE:
                stack[-1].close()


def handle_window_blur_event(e):
    if len(stack) > 0:
        looks_like_menu = stack[-1].TRANSPARENT_BG and stack[-1].EXIT_ON_CLICK_OUTSIDE
        if looks_like_menu:
            stack[-1].close()


def str_date_to_time_int(d):
    year, month, day = d.split("-")
    return dt.to_time_int(window.Date(int(year), int(month) - 1, int(day)))


def _browser_history_popstate():
    """When we get into our "first state", we either close the toplevel
    dialog, or go back another step. We also prevent the user from
    navigating with hashes.
    """
    h = window.history
    if h.state and h.state.tt_state:
        if h.state.tt_state == 1:
            if len(stack) > 0:
                h.pushState(
                    {"tt_state": 2}, window.document.title, window.location.pathname
                )
                stack[-1].close()
            else:
                h.back()
    elif window.location.hash:  # also note the hashchange event
        h.back()


def _browser_history_init():
    """Initialize history. Also take into account that we may come
    here when the user hit back or forward. Basically, we define two
    history states, one with tt_state == 1, and one tt_state == 2. The
    app is nearly always in the latter state. The first is only reached
    briefly when the user presses the back button.
    """
    h = window.history
    if h.state and h.state.tt_state:
        if h.state.tt_state == 1:
            h.pushState(
                {"tt_state": 2}, window.document.title, window.location.pathname
            )
    else:
        h.replaceState({"tt_state": 1}, window.document.title, window.location.pathname)
        h.pushState({"tt_state": 2}, window.document.title, window.location.pathname)

    # Now its safe to listen to history changes
    window.addEventListener("popstate", _browser_history_popstate, 0)


_browser_history_init()


def copy_dom_node(node):
    global document

    # Select the node (https://stackoverflow.com/questions/400212)
    sel = None
    if document.createRange and window.getSelection:  # FF, Chrome, Edge, ...
        range = document.createRange()
        sel = window.getSelection()
        sel.removeAllRanges()
        try:
            range.selectNodeContents(node)
            sel.addRange(range)
        except Exception:
            range.selectNode(node)
            sel.addRange(range)
    elif document.body.createTextRange:  # IE?
        range = document.body.createTextRange()
        range.moveToElementText(node)
        range.select()

    # Make a copy
    try:
        successful = window.document.execCommand("copy")
    except Exception:
        successful = False

    if not successful:
        return  # Don't unselect, user can now copy
    if sel is not None:
        sel.removeAllRanges()


def csvsplit(s, sep, i=0):
    """Split a string on the given sep, but take escaping with double-quotes
    into account. Double-quotes themselves can be escaped by duplicating them.
    The resuturned parts are whitespace-trimmed.
    """
    # https://www.iana.org/assignments/media-types/text/tab-separated-values
    # The only case we fail on afaik is tab-seperated values with a value
    # that starts with a quote. Spreadsheets seem not to escape these values.
    # This would make sense if they'd simply never quote TSV as seems to be the
    # "standard", but they *do* use quotes when the value has tabs or newlines :'(
    # In our own exports, we don't allow tabs or newlines, nor quotes at the start,
    # so we should be fine with our own data.
    global RawJS
    parts = []
    RawJS(
        """
    var mode = 0; // 0: between fields, 1: unescaped, 2: escaped
    var sepcode = sep.charCodeAt(0);
    var lastsplit = i;
    i -= 1;
    while (i < s.length - 1) {
        i += 1;
        var cc = s.charCodeAt(i);
        if (mode == 0) {
            if (cc == 34) { // quote
                mode = 2;
            } else if (cc == sepcode) { // empty value
                parts.push("");
                lastsplit = i + 1;
            } else if (cc == 9 || cc == 32 || cc == 13) {
                // ignore whitespace
            } else if (cc == 10) {
                break;  // next line
            } else {
                mode = 1; // unescaped value
            }
        } else if (mode == 1) {
            if (cc == sepcode) {
                parts.push(s.slice(lastsplit, i).trim());
                lastsplit = i + 1;
                mode = 0;
            } else if (cc == 10) {
                mode = 0;
                break;  // next line
            }
        } else { // if (mode == 2)
            if (cc == 34) { // end of escape, unless next char is also a quote
                if (i < s.length - 1 && s.charCodeAt(i + 1) == 34) {
                    i += 1; // Skip over second quote
                } else {
                    mode = 1;
                }
            }
        }
    }
    i += 1;
    parts.push(s.slice(lastsplit, i).trim());
    // Remove escape-quotes
    for (var j=0; j<parts.length; j++) {
        var val = parts[j];
        if (val.length > 0 && val[0] == '"' && val[val.length-1] == '"') {
            parts[j] = val.slice(1, val.length-1).replace('""', '"');
        }
    }
    """
    )
    return parts, i


class BaseDialog:
    """A dialog is widget that is shown as an overlay over the main application.
    Interaction with the application is disabled.
    """

    MODAL = True
    EXIT_ON_CLICK_OUTSIDE = True
    TRANSPARENT_BG = False

    def __init__(self, canvas):
        self._canvas = canvas
        self._create_main_div()
        self._callback = None

    def _create_main_div(self):
        self.maindiv = window.document.createElement("form")
        self.maindiv.addEventListener("keydown", self._on_key, 0)
        self._canvas.node.parentNode.appendChild(self.maindiv)
        self.maindiv.className = "dialog"
        self.maindiv.setAttribute("tabindex", -1)

    def _show_dialog(self):
        self.maindiv.style.display = "block"

        def f():
            self.maindiv.style.opacity = 1

        window.setTimeout(f, 1)

    def _hide_dialog(self):
        self.maindiv.style.display = "none"
        self.maindiv.style.opacity = 0

    def is_shown(self):
        return self.maindiv.style.display == "block"

    def open(self, callback):
        self._callback = callback
        # Disable main app and any "parent" dialogs
        if self.MODAL:
            show_background_div(True, self.TRANSPARENT_BG)
        if stack:
            stack[-1]._hide_dialog()

        # Show this dialog and add it to the stack
        self._show_dialog()
        stack.append(self)
        self.maindiv.focus()

    def submit(self, *args):
        # Close and call back
        callback = self._callback
        self._callback = None
        self.close()
        if callback is not None:
            callback(*args)

    def close(self, e=None):
        """Close/cancel/hide the dialog."""
        # Hide, and remove ourselves from the stack (also if not at the end)
        self._hide_dialog()
        for i in reversed(range(len(stack))):
            if stack[i] is self:
                stack.pop(i)

        # Give conrol back to parent dialog, or to the main app
        if stack:
            stack[-1]._show_dialog()
        for d in stack:
            if d.MODAL:
                show_background_div(True, d.TRANSPARENT_BG)
                break
        else:
            show_background_div(False)
        # Fire callback
        if self._callback is not None:
            self._callback()
            self._callback = None

    def _on_key(self, e):
        if e.key.lower() == "escape":
            self.close()


class DemoInfoDialog(BaseDialog):
    """Dialog to show as the demo starts up."""

    EXIT_ON_CLICK_OUTSIDE = True

    def open(self):
        """Show/open the dialog ."""
        html = """
            <h1>Demo
                <button type='button'><i class='fas'>\uf00d</i></button>
            </h1>
            <p>
            This demo shows 5 years of randomly generated time tracking data.
            Have a look around!
            </p><p>
            <i>Hit Escape or click anywhere outside of this dialog to close it.</i>
            </p>
        """
        self.maindiv.innerHTML = html

        close_but = self.maindiv.children[0].children[-1]
        close_but.onclick = self.close
        super().open(None)


class SandboxInfoDialog(BaseDialog):
    """Dialog to show as the sandbox starts up."""

    EXIT_ON_CLICK_OUTSIDE = True

    def open(self):
        """Show/open the dialog ."""
        html = """
            <h1>Sandbox
                <button type='button'><i class='fas'>\uf00d</i></button>
            </h1>
            <p>
            The TimeTagger sandbox starts without any records. You can play around
            or try importing records. The data is not synced to the server and
            will be lost as soon as you leave this page.
            </p><p>
            <i>Hit Escape or click anywhere outside of this dialog to close it.</i>
            </p>
        """
        self.maindiv.innerHTML = html

        close_but = self.maindiv.children[0].children[-1]
        close_but.onclick = self.close
        super().open(None)


class NotificationDialog(BaseDialog):
    """Dialog to show a message to the user."""

    EXIT_ON_CLICK_OUTSIDE = True

    def open(self, message):
        """Show/open the dialog ."""
        html = f"""
            <h1>Notification
                <button type='button'><i class='fas'>\uf00d</i></button>
            </h1>
            <p>{message}</p>
        """
        self.maindiv.innerHTML = html
        close_but = self.maindiv.children[0].children[-1]
        close_but.onclick = self.close
        super().open(None)


class MenuDialog(BaseDialog):
    """Dialog to show a popup menu."""

    EXIT_ON_CLICK_OUTSIDE = True
    TRANSPARENT_BG = True

    def open(self):
        """Show/open the dialog ."""

        # Put the menu right next to the menu button
        self.maindiv.style.top = "5px"
        self.maindiv.style.left = "50px"

        self.maindiv.innerHTML = f"""
            <div class='loggedinas'></div>
            <div class='divider'></div>
            <a href="/"><img style='width:20px; height:20px;vertical-align:middle;' src='timetagger_sd.svg' />&nbsp;&nbsp;Homepage</a>
            <a href="https://timetagger.app/support"><i class='fas'>\uf059</i>&nbsp;&nbsp;Get tips and help</a>
            <a href="../account"><i class='fas'>\uf2bd</i>&nbsp;&nbsp;Account</a>
            <div class='divider'></div>
        """.rstrip()

        # Unpack
        loggedinas = self.maindiv.children[0]

        # Valid store?
        if window.store.get_auth:
            logged_in = store_valid = bool(window.store.get_auth())
        else:
            store_valid = True
            logged_in = False
            # logged_in = bool(window.auth.get_auth_info())
        logged_in  # noqaM

        is_installable = window.pwa and window.pwa.deferred_prompt

        # <a href="login"><i class='fas'>\uf2f6</i>&nbsp;&nbsp;Login</a>
        # <a href="logout"><i class='fas'>\uf2f5</i>&nbsp;&nbsp;Logout</a>
        # # Hide login or logout button, or both
        # loginbut = self.maindiv.children[3]
        # logoutbut = self.maindiv.children[4]
        # if logged_in:
        #     loginbut.style.display = "none"
        # else:
        #     logoutbut.style.display = "none"

        # Display sensible text in "header"
        if window.store.__name__.startswith("Demo"):
            text = "This is the Demo"
        elif window.store.__name__.startswith("Sandbox"):
            text = "This is the Sandbox"
        elif window.store.get_auth:
            auth = window.store.get_auth()
            if auth:
                text = "Signed in as " + auth.email
            else:
                text = "Not signed in"
        if window.timetaggerversion:
            text += " - TimeTagger " + window.timetaggerversion
        loggedinas.innerText = text

        container = self.maindiv
        for icon, isvalid, title, func in [
            ("\uf013", store_valid, "Settings", self._show_settings),
            ("\uf02c", store_valid, "Search & manage tags", self._manage_tags),
            ("\uf56f", store_valid, "Import records", self._import),
            ("\uf56e", store_valid, "Export all records", self._export),
            (
                "\uf3fa",
                is_installable,
                "<span class='acc_color'>Install this app</span>",
                self._do_install,
            ),
        ]:
            if not isvalid:
                continue
            elif title is None:
                el = window.document.createElement("div")
                el.setAttribute("class", "divider")
                container.appendChild(el)
            else:
                el = window.document.createElement("a")
                el.innerHTML = f"<i class='fas'>{icon}</i>&nbsp;&nbsp;{title}"
                el.onclick = func
                container.appendChild(el)

        # more: Settings, User account, inport / export

        self.maindiv.classList.add("verticalmenu")
        super().open(None)

    def _show_settings(self):
        self.close()
        self._canvas.settings_dialog.open()

    def _do_install(self):
        # There are quite a few components to make installation as a
        # PWA possible. In our case:
        # * We have a timetagger_manifest.json
        # * We <link> to it in the template so it can be discovered.
        # * We have a service worker in sw.js, which we activate it in app.md.
        # * In app.md we also do the PWA beforeinstallprompt dance so that in
        #   here we can detect whether it's installable and trigger the install
        self.close()
        window.pwa.install()

    def _open_report(self):
        self.close()
        t1, t2 = self._canvas.range.get_range()
        prname = self._canvas.widgets["AnalyticsWidget"].selected_tag_name
        self._canvas.report_dialog.open(t1, t2, prname)

    def _manage_tags(self):
        self.close()
        self._canvas.tag_manage_dialog.open()

    def _export(self):
        self.close()
        self._canvas.export_dialog.open()

    def _import(self):
        self.close()
        self._canvas.import_dialog.open()


class TimeSelectionDialog(BaseDialog):
    """Dialog to show a popup for selecting the time range."""

    EXIT_ON_CLICK_OUTSIDE = True
    TRANSPARENT_BG = True

    def open(self):
        """Show/open the dialog ."""

        # Transform time int to dates.
        t1, t2 = self._canvas.range.get_target_range()
        t1_date = dt.time2localstr(dt.floor(t1, "1D")).split(" ")[0]
        t2_date = dt.time2localstr(dt.round(t2, "1D")).split(" ")[0]
        if t1_date != t2_date:
            # The date range is inclusive (and we add 1D later): move back one day
            t2_date = dt.time2localstr(dt.add(dt.round(t2, "1D"), "-1D")).split(" ")[0]

        # Generate preamble
        html = f"""
            <div class='grid5'>
                <a>today [d]</a>
                <a>this week [w]</a>
                <a>this month [m]</a>
                <a>this quarter</a>
                <a>this year</a>
                <a>yesterday</a>
                <a>last week</a>
                <a>last month</a>
                <a>last quarter</a>
                <a>last year</a>
            </div>
            <div style='min-height: 8px;'></div>
            <div class='menu'>
                <div style='flex: 0.5 0.5 auto; text-align: right;'>From:&nbsp;&nbsp;</div>
                <input type="date" step="1" />
                <div style='flex: 0.5 0.5 auto; text-align: right;'>To:&nbsp;&nbsp;</div>
                <input type="date" step="1" />
                <div style='flex: 0.5 0.5 auto;'></div>
            </div>
            <div style='min-height: 8px;'></div>
        """

        self.maindiv.innerHTML = html
        presets = self.maindiv.children[0]
        form = self.maindiv.children[2]

        self._t1_input = form.children[1]
        self._t2_input = form.children[3]

        for i in range(presets.children.length):
            but = presets.children[i]
            but.onclick = lambda e: self._apply_preset(e.target.innerText)

        self._t1_input.value = t1_date
        self._t1_input.oninput = self._update_range
        self._t2_input.value = t2_date
        self._t2_input.oninput = self._update_range

        self.maindiv.classList.add("verticalmenu")
        super().open(None)

    def _apply_preset(self, text):
        text = text.lower()
        last = text.count("last")
        if text.count("today"):
            rounder = "1D"
        elif text.count("yesterday"):
            rounder = "1D"
            last = True
        elif text.count("week"):
            rounder = "1W"
        elif text.count("month"):
            rounder = "1M"
        elif text.count("quarter"):
            rounder = "3M"
        elif text.count("year"):
            rounder = "1Y"
        else:
            return

        t1 = dt.floor(dt.now(), rounder)
        if last:
            t1 = dt.add(t1, "-" + rounder)
        t2 = dt.add(t1, rounder)
        t2 = dt.add(t2, "-1D")  # range is inclusive

        self._t1_input.value = dt.time2localstr(t1).split(" ")[0]
        self._t2_input.value = dt.time2localstr(t2).split(" ")[0]
        self._update_range()
        self.close()

    def _update_range(self):
        t1_date = self._t1_input.value
        t2_date = self._t2_input.value
        if not float(t1_date.split("-")[0]) > 1899:
            return
        elif not float(t2_date.split("-")[0]) > 1899:
            return

        t1 = str_date_to_time_int(t1_date)
        t2 = str_date_to_time_int(t2_date)
        if t1 > t2:
            t1, t2 = t2, t1
        t2 = dt.add(t2, "1D")  # look until the end of the day

        window.canvas.range.animate_range(t1, t2, None, False)  # without snap


class StartStopEdit:
    """Helper class to allow the user to set the start and stop time of a record."""

    def __init__(self, node, callback, t1, t2, mode):
        self.node = node
        self.callback = callback
        self.initialmode = mode.lower()
        self.initial_t1, self.initial_t2 = t1, t2  # even more original than ori_t1 :)

        if self.initialmode in ("start", "new"):
            text_startnow = "Start now"
            text_startrlr = "Started earlier"
            text_finished = "Already done"
        else:
            text_startnow = "Start now"  # not visible
            text_startrlr = "Still running"
            text_finished = "Stopped"

        self.node.innerHTML = f"""
        <div>
            <label style='user-select:none;'><input type='radio' name='runningornot' />&nbsp;{text_startnow}&nbsp;&nbsp;</label>
            <label style='user-select:none;'><input type='radio' name='runningornot' />&nbsp;{text_startrlr}&nbsp;&nbsp;</label>
            <label style='user-select:none;'><input type='radio' name='runningornot' />&nbsp;{text_finished}&nbsp;&nbsp;</label>
            <div style='min-height:1em;'></div>
        </div>
        <div>
        <span><i class='fas' style='color:#999; vertical-align:middle;'>\uf144</i></span>
            <input type='date' step='1'  style='font-size: 80%;' />
            <span style='display: flex;'>
                <input type='text' style='flex:1; min-width: 50px; font-size: 80%;' />
                <button type='button' style='width:2em; margin-left:-1px;'>+</button>
                <button type='button' style='width:2em; margin-left:-1px;'>-</button>
                </span>
            <span></span>
        <span><i class='fas' style='color:#999; vertical-align:middle;'>\uf28d</i></span>
            <input type='date' step='1' style='font-size: 80%;' />
            <span style='display: flex;'>
                <input type='text' style='flex:1; min-width: 50px; font-size: 80%;' />
                <button type='button' style='width:2em; margin-left:-1px;'>+</button>
                <button type='button' style='width:2em; margin-left:-1px;'>-</button>
                </span>
            <span></span>
        <span><i class='fas' style='color:#999; vertical-align:middle;'>\uf2f2</i></span>
            <span></span>
            <input type='text' style='flex: 1; min-width: 50px' />
            <span></span>
        </div>
        """

        # Unpack children
        self.radionode = self.node.children[0]
        self.gridnode = self.node.children[1]
        self.radio_startnow = self.radionode.children[0].children[0]
        self.radio_startrlr = self.radionode.children[1].children[0]
        self.radio_finished = self.radionode.children[2].children[0]
        (
            _,  # date and time 1
            self.date1input,
            self.time1stuff,
            _,
            _,  # date and time 2
            self.date2input,
            self.time2stuff,
            _,
            _,  # duration
            _,
            self.durationinput,
            _,
        ) = self.gridnode.children

        self.time1input, self.time1more, self.time1less = self.time1stuff.children
        self.time2input, self.time2more, self.time2less = self.time2stuff.children

        # Tweaks
        for but in (self.time1less, self.time1more, self.time2less, self.time2more):
            but.setAttribute("tabIndex", -1)

        # Styling
        self.gridnode.style.display = "grid"
        self.gridnode.style.gridTemplateColumns = "auto 130px 140px 2fr"
        self.gridnode.style.gridGap = "4px 0.5em"
        self.gridnode.style.justifyItems = "stretch"
        self.gridnode.style.alignItems = "stretch"

        # Set visibility of mode-radio-buttons
        if self.initialmode == "start":
            self.radio_startnow.setAttribute("checked", True)
        elif self.initialmode == "new":
            self.radio_finished.setAttribute("checked", True)
        elif self.initialmode == "stop":
            self.radio_finished.setAttribute("checked", True)
            self.radio_startnow.parentNode.style.display = "none"
        elif t1 == t2:
            self.radio_startrlr.setAttribute("checked", True)
            self.radio_startnow.parentNode.style.display = "none"
        else:
            self.radio_finished.setAttribute("checked", True)
            self.radionode.style.display = "none"

        # Connect events
        self.radio_startnow.onclick = self._on_mode_change
        self.radio_startrlr.onclick = self._on_mode_change
        self.radio_finished.onclick = self._on_mode_change
        self.date1input.onchange = lambda: self.onchanged("date1")
        self.time1input.onchange = lambda: self.onchanged("time1")
        self.date2input.onchange = lambda: self.onchanged("date2")
        self.time2input.onchange = lambda: self.onchanged("time2")
        self.durationinput.onchange = lambda: self.onchanged("duration")
        self.time1more.onclick = lambda: self.onchanged("time1more")
        self.time1less.onclick = lambda: self.onchanged("time1less")
        self.time2more.onclick = lambda: self.onchanged("time2more")
        self.time2less.onclick = lambda: self.onchanged("time2less")

        self.reset(t1, t2)
        self._timer_handle = window.setInterval(self._update_duration, 200)

    def close(self):
        window.clearInterval(self._timer_handle)

    def _on_mode_change(self):
        if self.initialmode in ("start", "new"):
            # Get sensible earlier time
            t2 = dt.now()
            t1 = t2 - 5 * 3600
            records = window.store.records.get_records(t1, t2).values()
            records.sort(key=lambda r: r.t2)
            if len(records) > 0:
                t1 = records[-1].t2  # start time == last records stop time
                t1 = min(t1, t2 - 1)
            else:
                t1 = t2 - 3600  # start time is an hour ago
            # Apply
            if self.radio_startnow.checked:
                self.reset(t2, t2)
            elif self.radio_startrlr.checked:
                self.reset(t1, t1)
            else:
                self.reset(t1, t2)
        else:
            # Switch between "already running" and "finished".
            # Since this is an existing record, we should maintain initial values.
            if self.radio_startrlr.checked:
                self.reset(self.initial_t1, self.initial_t1)
            else:
                t2 = max(self.initial_t1 + 1, dt.now())
                self.reset(self.initial_t1, t2)

    def reset(self, t1, t2):
        """Reset with a given t1 and t2."""

        # Store originals
        self.ori_t1 = self.t1 = t1
        self.ori_t2 = self.t2 = t2

        # Get original dates and (str) times
        self.ori_date1, self.ori_time1 = dt.time2localstr(self.t1).split(" ")
        self.ori_date2, self.ori_time2 = dt.time2localstr(self.t2).split(" ")
        self.ori_days2 = self.days2 = self._days_between_dates(
            self.ori_date1, self.ori_date2
        )

        # Store original str duration
        t = t2 - t1
        self.ori_duration = f"{t//3600:.0f}h {(t//60)%60:02.0f}m {t%60:02.0f}s"

        self._set_time_input_visibility()
        self.render()
        window.setTimeout(self.callback, 1)

    def _set_time_input_visibility(self):
        def show_subnode(i, show):
            subnode = self.gridnode.children[i]
            if not show:
                subnode.style.display = "none"
            elif i % 4 == 2:
                subnode.style.display = "flex"
            else:
                subnode.style.display = "inline-block"

        for i in range(0, 4):
            show_subnode(i, not self.radio_startnow.checked)
        for i in range(4, 8):
            show_subnode(i, self.radio_finished.checked)
        for i in range(8, 12):
            show_subnode(i, not self.radio_startnow.checked)

    def _update_duration(self):
        if self.t1 == self.t2:
            t = dt.now() - self.t1
            self.durationinput.value = (
                f"{t//3600:.0f}h {(t//60)%60:02.0f}m {t%60:02.0f}s"
            )

    def _days_between_dates(self, d1, d2):
        year1, month1, day1 = d1.split("-")
        year2, month2, day2 = d2.split("-")
        dt1 = window.Date(year1, month1 - 1, day1).getTime()
        for extraday in range(100):
            dt2 = window.Date(year2, month2 - 1, day2 - extraday).getTime()
            if dt1 == dt2:
                return extraday
        else:
            return 0  # more than 100 days ... fall back to zero?

    def _timestr2tuple(self, s):
        s = RawJS('s.split(" ").join("") + ":"')  # remove whitespace
        s = RawJS('s.replace(":", "h").replace(":", "m").replace(":", "s")')
        s = RawJS(
            's.replace("h", "h ").replace("m", "m ").replace("s", "s ").replace(":", ": ")'
        )
        hh = mm = ss = 0
        for part in s.split(" "):
            if len(part) > 1:
                if part.endsWith("h"):
                    hh = int(part[:-1])
                elif part.endsWith("m"):
                    mm = int(part[:-1])
                    if isNaN(mm):
                        mm = 0
                elif part.endsWith("s"):
                    ss = int(part[:-1])
                    if isNaN(ss):
                        ss = 0
        if isNaN(hh) or isNaN(mm) or isNaN(ss):
            return None, None, None
        return hh, mm, ss

    def _get_time(self, what):
        node = self[what + "input"]
        hh = mm = ss = None
        if node.value:
            hh, mm, ss = self._timestr2tuple(node.value)
        if hh is None:
            if what == "time2":
                self.days2 = self.ori_days2  # rest along with time2
            hh, mm, ss = self._timestr2tuple(self["ori_" + what])
        return hh, mm, ss

    def render(self):
        now = dt.now()

        # Get date/time info
        t1_date, t1_time = dt.time2localstr(self.t1).split(" ")
        t2_date, t2_time = dt.time2localstr(self.t2).split(" ")
        now_date, now_time = dt.time2localstr(now).split(" ")

        # Set date and time for t1
        self.date1input.value = t1_date
        self.time1input.value = t1_time[:5] if t1_time.endsWith("00") else t1_time
        self.days2 = self._days_between_dates(t1_date, t2_date)

        # Set stop time and duration
        if self.t1 == self.t2:
            # Is running
            t = now - self.t1
            self.time2input.disabled = True
            self.date2input.disabled = True
            self.durationinput.disabled = True
            self.date2input.value = now_date
            self.time2input.value = "running"
            self._update_duration()  # use method that we also use periodically
        else:
            # Is not running
            t = self.t2 - self.t1
            self.time2input.disabled = False
            self.date2input.disabled = False
            self.durationinput.disabled = False
            self.date2input.value = t2_date
            self.time2input.value = t2_time[:5] if t2_time.endsWith("00") else t2_time
            if t % 60 == 0:
                m = Math.round((self.t2 - self.t1) / 60)
                self.durationinput.value = f"{m//60:.0f}h {m%60:02.0f}m"
            else:
                self.durationinput.value = (
                    f"{t//3600:.0f}h {(t//60)%60:02.0f}m {t%60:02.0f}s"
                )

        # Tweak bgcolor of date2 field to hide it a bit
        if self.days2 == 0:
            self.date2input.style.color = "#888"
        else:
            self.date2input.style.color = None

    def onchanged(self, action):
        now = dt.now()

        # Get node
        if action.endsWith("more") or action.endsWith("less"):
            what = action[:-4]
        else:
            what = action
        node = self[what + "input"]
        if not node:
            return

        # Get the reference dates
        if self.date1input.value:
            year1, month1, day1 = self.date1input.value.split("-")
        else:
            year1, month1, day1 = self.ori_date1.split("-")
        year1, month1, day1 = int(year1), int(month1), int(day1)
        #
        if self.date2input.value:
            year2, month2, day2 = self.date2input.value.split("-")
        else:
            year2, month2, day2 = self.ori_date2.split("-")
        year2, month2, day2 = int(year2), int(month2), int(day2)

        if what == "date1":
            # Changing date1 -> update both t1 and t2, date2 moves along
            hh, mm, ss = self._get_time("time1")
            d1 = window.Date(year1, month1 - 1, day1, hh, mm, ss)
            hh, mm, ss = self._get_time("time2")
            d2 = window.Date(year1, month1 - 1, day1 + self.days2, hh, mm, ss)
            self.t1 = dt.to_time_int(d1)
            self.t2 = dt.to_time_int(d2)
            if self.ori_t1 == self.ori_t2:
                self.t2 = self.t1
            elif self.t1 >= self.t2:
                self.t2 = self.t1 + 1

        elif what == "date2":
            # Changing date2 -> update only t2
            hh, mm, ss = self._get_time("time2")
            d2 = window.Date(year2, month2 - 1, day2, hh, mm, ss)
            self.t2 = dt.to_time_int(d2)
            if self.ori_t1 == self.ori_t2:
                self.t2 = self.t1
            elif self.t2 <= self.t1:
                self.t2 = self.t1 + 60

        elif what == "time1":
            # Changing time1 -> update t1, keep t2 in check
            hh, mm, ss = self._get_time("time1")
            if action.endsWith("more"):
                mm, ss = mm + 5, 0
            elif action.endsWith("less"):
                mm, ss = mm - 5, 0
            d1 = window.Date(year1, month1 - 1, day1, hh, mm, ss)
            self.t1 = dt.to_time_int(d1)
            if self.ori_t1 == self.ori_t2:
                self.t2 = self.t1 = min(self.t1, now)
            elif self.t1 >= self.t2:
                self.t2 = self.t1 + 1

        elif what == "time2":
            # Changing time2 -> update t2, keep t1 and t2 in check
            hh, mm, ss = self._get_time("time2")
            if action.endsWith("more"):
                mm, ss = mm + 5, 0
            elif action.endsWith("less"):
                mm, ss = mm - 5, 0
            d2 = window.Date(year2, month2 - 1, day2, hh, mm, ss)
            self.t2 = dt.to_time_int(d2)
            if self.ori_t1 == self.ori_t2:
                self.t2 = self.t1
            elif self.t2 <= self.t1:
                self.t1 = self.t2
                self.t2 = self.t1 + 1

        elif what == "duration":
            # Changing duration -> update t2, but keep it in check
            hh, mm, ss = self._get_time("duration")
            duration = hh * 3600 + mm * 60 + ss
            # Apply
            if self.ori_t1 == self.ori_t2:  # failsafe - keep running
                self.duration = 0
                self.t2 = self.t1
            elif duration < 0:
                self.t1 += duration
                self.t2 = self.t1 + 1
            elif not duration:  # Keep not-running
                self.t2 = self.t1 + 1
            else:
                self.t2 = self.t1 + duration

        # Invoke callback and rerender
        window.setTimeout(self.callback, 1)
        return self.render()


class RecordDialog(BaseDialog):
    """Dialog to allow modifying a record (setting description and times)."""

    def __init__(self, canvas):
        super().__init__(canvas)
        self._record = None
        self._no_user_edit_yet = True

    def open(self, mode, record, callback=None):
        """Show/open the dialog for the given record. On submit, the
        record will be pushed to the store and callback (if given) will
        be called with the record. On close/cancel, the callback will
        be called without arguments.
        """
        self._record = record.copy()
        assert mode.lower() in ("start", "new", "edit", "stop")

        html = f"""
            <h1><i class='fas'>\uf682</i>&nbsp;&nbsp;<span>Record</span>
                <button type='button'><i class='fas'>\uf00d</i></button>
            </h1>
            <h2><i class='fas'>\uf305</i>&nbsp;&nbsp;Description</h2>
            <input type='text' style='width: calc(100% - 4em);' spellcheck='false' />
            <div style='color:#777;'></div>
            <div></div>
            <h2><i class='fas'>\uf017</i>&nbsp;&nbsp;Time</h2>
            <div></div>
            <div style='margin-top:2em;'></div>
            <div style='display: flex;justify-content: flex-end;'>
                <button type='button' class='actionbutton'><i class='fas'>\uf00d</i>&nbsp;&nbsp;Cancel</button>
                <button type='button' class='actionbutton'><i class='fas'>\uf1f8</i>&nbsp;&nbsp;Delete</button>
                <button type='button' class='actionbutton'><i class='fas'>\uf24d</i>&nbsp;&nbsp;Resume</button>
                <button type='button' class='actionbutton submit'>Submit</button>
            </div>
            <button type='button' style='float:right;' class='actionbutton'>Confirm deleting this record</button>
        """
        self.maindiv.innerHTML = html

        # Unpack so we have all the components
        (
            h1,  # Dialog title
            _,  # Description header
            self._ds_input,
            self._tag_suggestions_div,
            self._tags_div,
            _,  # Time header
            self._time_node,
            _,  # Splitter
            self._buttons,
            self._delete_but2,
        ) = self.maindiv.children
        #
        self._title_div = h1.children[1]
        self._cancel_but1 = self.maindiv.children[0].children[-1]
        (
            self._cancel_but2,
            self._delete_but1,
            self._resume_but,
            self._submit_but,
        ) = self._buttons.children

        # Create the startstop-edit
        self._time_edit = StartStopEdit(
            self._time_node, self._on_times_change, record.t1, record.t2, mode
        )

        # Prepare some things to show suggested tags
        window._record_dialog_add_tag = self._record_dialog_add_tag
        self._suggested_tags_html = self._get_suggested_tags()
        self._suggested_tags_list = []  # for keyboard shortcuts

        # Set some initial values
        self._ds_input.value = record.get("ds", "")
        self._query_tags()
        self._delete_but2.style.display = "none"
        self._no_user_edit_yet = True

        # Show the right buttons
        self._set_mode(mode)

        # Connect things up
        self._cancel_but1.onclick = self.close
        self._cancel_but2.onclick = self.close
        self._submit_but.onclick = self.submit
        self._resume_but.onclick = self.resume_record
        self._ds_input.oninput = self._on_user_edit
        self._ds_input.onchange = self._on_user_edit_done
        self._delete_but1.onclick = self._delete1
        self._delete_but2.onclick = self._delete2

        # Enable for some more info (e.g. during dev)
        if False:
            for x in [f"ID: {record.key}", f"Modified: {dt.time2localstr(record.mt)}"]:
                el = window.document.createElement("div")
                el.innerText = x
                self.maindiv.appendChild(el)

        # Almost done. Focus on ds if this looks like desktop; it's anoying on mobile
        super().open(callback)
        if utils.looks_like_desktop():
            self._ds_input.focus()

    def _set_mode(self, mode):
        self._lmode = lmode = mode.lower()
        self._title_div.innerText = f"{mode} record"
        is_running = self._record.t1 == self._record.t2
        # has_running = len(window.store.records.get_running_records()) > 0
        # Set description placeholder
        if lmode == "start":
            self._ds_input.setAttribute("placeholder", "What are you going to do?")
        elif lmode == "new":
            self._ds_input.setAttribute("placeholder", "What have you done?")
        elif lmode == "stop":
            self._ds_input.setAttribute("placeholder", "What did you just do?")
        elif is_running:
            self._ds_input.setAttribute("placeholder", "What are you doing?")
        else:
            self._ds_input.setAttribute("placeholder", "What has been done?")
        # Tweak the buttons at the bottom
        if lmode == "start":
            self._submit_but.innerHTML = "<i class='fas'>\uf04b</i>&nbsp;&nbsp;Start"
            self._resume_but.style.display = "none"
            self._delete_but1.style.display = "none"
        elif lmode == "new":
            self._submit_but.innerHTML = "<i class='fas'>\uf067</i>&nbsp;&nbsp;Create"
            self._resume_but.style.display = "none"
            self._delete_but1.style.display = "none"
        elif lmode == "edit":
            self._submit_but.innerHTML = "<i class='fas'>\uf304</i>&nbsp;&nbsp;Edit"
            title_mode = "Edit running" if is_running else "Edit"
            self._title_div.innerText = f"{title_mode} record"
            self._submit_but.disabled = self._no_user_edit_yet
            self._resume_but.style.display = "none" if is_running else "block"
            self._delete_but1.style.display = "block"
        elif lmode == "stop":
            self._submit_but.innerHTML = "<i class='fas'>\uf04d</i>&nbsp;&nbsp;Stop"
            self._resume_but.style.display = "none"
            self._delete_but1.style.display = "block"
        else:
            console.warn("Unexpected record dialog mode " + mode)

    def _on_user_edit(self):
        self._query_tags()
        if self._no_user_edit_yet:
            self._no_user_edit_yet = False
            self._submit_but.disabled = False

    def _on_user_edit_done(self):
        ds = to_str(self._ds_input.value)
        _, parts = utils.get_tags_and_parts_from_string(ds)
        self._ds_input.value = parts.join("")

    def _on_times_change(self):
        was_running = self._record.t1 == self._record.t2
        self._record.t1 = self._time_edit.t1
        self._record.t2 = self._time_edit.t2
        is_running = self._record.t1 == self._record.t2
        self._on_user_edit()
        # Swap mode?
        if was_running and not is_running:
            if self._lmode == "start":
                self._set_mode("New")
            else:
                self._set_mode("Stop")
        elif is_running and not was_running:
            if self._lmode == "new":
                self._set_mode("Start")
            else:
                self._set_mode("Edit")

    def _query_tags(self):
        """Get all current tags. If different, update suggestions. """
        # Show info about current tags in description
        tags, parts = utils.get_tags_and_parts_from_string(self._ds_input.value)
        tags_html = "Tags: "
        if len(tags) == 0:
            tags = ["#untagged"]
        tags_list = [f"<span style='color:#000'>{t}</span>" for t in tags]
        tags_html += "&nbsp; &nbsp;".join(tags_list)
        # Get suggested tags
        self._suggested_tags_list = []
        if self._suggested_tags_html:
            suggested_dict = self._suggested_tags_html.copy()
            for tag in tags:
                suggested_dict.pop(tag, None)
            self._suggested_tags_list = suggested_dict.keys()[:6]
            suggested_html = "Suggested tags:"
            for i, tag in enumerate(self._suggested_tags_list):
                html = suggested_dict[tag].replace(">#", f">{i + 1}: ")
                suggested_html += "&nbsp; &nbsp;" + html
        else:
            suggested_html = "Use e.g. '&#35;meeting' to add one or more tags."
        # Detect duplicate tags
        tag_counts = {}
        for part in parts:
            if part.startswith("#"):
                tag_counts[part] = tag_counts.get(part, 0) + 1
        duplicates = [tag for tag, count in tag_counts.items() if count > 1]
        if len(duplicates):
            suggested_html += "<br>Duplicate tags: " + duplicates.join(" ")
        # Apply
        self._tag_suggestions_div.innerHTML = suggested_html
        self._tags_div.innerHTML = tags_html

    def _record_dialog_add_tag(self, tag):
        self._ds_input.value = self._ds_input.value.rstrip() + " " + tag + " "
        self._on_user_edit()
        if utils.looks_like_desktop():
            self._ds_input.focus()

    def close(self, e=None):
        self._time_edit.close()
        super().close(e)

    def _on_key(self, e):
        key = e.key.lower()
        if key == "enter" or key == "return":
            self.submit()
        elif key in "123456789" and (e.ctrlKey or e.metaKey):
            try:
                index = int(key) - 1
            except Exception:
                return
            if 0 <= index < len(self._suggested_tags_list):
                tag = self._suggested_tags_list[index]
                self._record_dialog_add_tag(tag)
                e.preventDefault()  # don't insert the digit
        else:
            super()._on_key(e)

    def _get_suggested_tags(self, max_suggestions=16):
        # Get history of records
        t2 = dt.now()
        t1 = t2 - 12 * 7 * 24 * 3600  # 12 weeks, about a quarter year
        records = window.store.records.get_records(t1, t2)
        # Collect all tags and a corresponding score
        tags_to_scores = {}
        for r in records.values():
            tags, _ = utils.get_tags_and_parts_from_string(r.ds)
            score = 1 / (t2 - r.t1)
            for tag in tags:
                tags_to_scores[tag] = (tags_to_scores[tag] | 0) + score
        # Put in a list
        score_tag_list = []
        for tag, score in tags_to_scores.items():
            if tag == "#untagged":
                continue
            score_tag_list.append((score, tag))
        # Sort by score and trim names
        score_tag_list.sort(key=lambda x: -x[0])
        tag_names = [score_tag[1] for score_tag in score_tag_list[:max_suggestions]]
        # Turn into html
        html_parts = {}
        for tag in tag_names:
            x = f"<a onclick='window._record_dialog_add_tag(\"{tag}\")' "
            x += f"style='cursor:pointer;'"
            x += ">" + tag + "</a>"
            html_parts[tag] = x
        return html_parts

    def _delete1(self):
        self._delete_but2.style.display = "block"

    def _delete2(self):
        record = self._record
        window.stores.make_hidden(record)  # Sets the description
        record.t2 = record.t1 + 1  # Set duration to 1s (t1 == t2 means running)
        window.store.records.put(record)
        self.close(record)

    def _stop_all_running_records(self):
        records = window.store.records.get_running_records()
        now = dt.now()
        for record in records:
            record.t2 = max(record.t1 + 10, now)
            window.store.records.put(record)

    def submit(self):
        """Submit the record to the store."""
        # Submit means close if there was nothing to submit
        if self._submit_but.disabled:
            return self.close()
        # Set record.ds
        _, parts = utils.get_tags_and_parts_from_string(to_str(self._ds_input.value))
        self._record.ds = parts.join("")
        if not self._record.ds:
            self._record.pop("ds", None)
        # Prevent multiple timers at once
        if self._record.t1 == self._record.t2:
            self._stop_all_running_records()
        # Apply
        window.store.records.put(self._record)
        super().submit(self._record)

    def resume_record(self):
        """Start a new record with the same description."""
        # The resume button should only be visible for non-running records, but
        # if (for whatever reason) this gets called, resume will mean leave running.
        if self._record.t1 == self._record.t2:
            return self.submit()
        # In case other timers are runnning, stop these!
        self._stop_all_running_records()
        # Create new record with current description
        now = dt.now()
        record = window.store.records.create(now, now)
        _, parts = utils.get_tags_and_parts_from_string(to_str(self._ds_input.value))
        record.ds = parts.join("")
        window.store.records.put(record)
        # Close the dialog - don't apply local changes
        self.close()


class ColorDialog(BaseDialog):
    """Dialog to set the color for a tag combination."""

    def open(self, tagz, callback=None):

        # Put in deterministic order
        tags = tagz.split(" ")
        tags.sort()
        self._tagz = tagz = tags.join(" ")

        self._default_color = utils.color_from_name(self._tagz)

        self.maindiv.innerHTML = f"""
            <h1><i class='fas'>\uf53f</i>&nbsp;&nbsp;Set color for {tagz}
                <button type='button'><i class='fas'>\uf00d</i></button>
                </h1>
            <input type='text' style='width: 210px; border: 5px solid #eee' spellcheck='false' />
            <br>
            <button type='button'><i class='fas'>\uf12d</i> Auto</button>
            <button type='button' style='margin-left: 2px'><i class='fas'>\uf2f1</i> Random</button>
            <br>
            <div style='display: inline-grid; grid-gap: 2px;'></div>
            <div style='margin-top:2em;'></div>
            <div style='display: flex;justify-content: flex-end;'>
                <button type='button' class='actionbutton'><i class='fas'>\uf00d</i>&nbsp;&nbsp;Cancel</button>
                <button type='button' class='actionbutton submit'><i class='fas'>\uf00c</i>&nbsp;&nbsp;Apply</button>
            </div>
        """

        close_but = self.maindiv.children[0].children[-1]

        (
            _,  # h1
            self._color_input,
            _,  # br
            self._default_button,
            self._random_button,
            _,  # br
            self._color_grid,
            _,  # gap
            buttons,
        ) = self.maindiv.children

        # Connect things up
        close_but.onclick = self.close
        buttons.children[0].onclick = self.close
        buttons.children[1].onclick = self.submit
        self._color_input.onchange = lambda: self._set_color(self._color_input.value)
        self._default_button.onclick = self._set_default_color
        self._random_button.onclick = self._set_random_color

        # Generate palette
        self._color_grid.style.gridTemplateColumns = "auto ".repeat(utils.PALETTE_COLS)
        for hex in utils.PALETTE2:
            el = document.createElement("span")
            el.style.background = hex
            el.style.width = "30px"
            el.style.height = "30px"
            self._make_clickable(el, hex)
            self._color_grid.appendChild(el)

        self._set_color(window.store.settings.get_color_for_tagz(tagz))

        super().open(callback)
        if utils.looks_like_desktop():
            self._color_input.focus()
            self._color_input.select()

    def _on_key(self, e):
        key = e.key.lower()
        if key == "enter" or key == "return":
            e.preventDefault()
            self.submit()
        else:
            super()._on_key(e)

    def _make_clickable(self, el, hex):
        # def clickcallback():
        #     self._color_input.value = hex
        el.onclick = lambda: self._set_color(hex)

    def _set_default_color(self):
        self._set_color(self._default_color)

    def _set_random_color(self):
        clr = "#" + Math.floor(Math.random() * 16777215).toString(16)
        self._set_color(clr)

    def _set_color(self, clr):
        if not clr or clr.lower() in ["auto", "undefined", "null"]:
            clr = self._default_color
        if clr != self._color_input.value:
            self._color_input.value = clr
        self._color_input.style.borderColor = clr

    def submit(self):
        clr = self._color_input.value
        cur_color = window.store.settings.get_color_for_tagz(self._tagz)
        if clr != cur_color:
            if clr == self._default_color:
                window.store.settings.set_color_for_tagz(self._tagz, "")
            else:
                window.store.settings.set_color_for_tagz(self._tagz, clr)
        super().submit()


class TagManageDialog(BaseDialog):
    """Dialog to manage tags."""

    def open(self):

        self.maindiv.innerHTML = """
            <h1><i class='fas'>\uf02b</i>&nbsp;&nbsp;Search & manage tags
                <button type='button'><i class='fas'>\uf00d</i></button>
                </h1>
            <p>This tool allows you to search records by tag name(s), and to
            rename/remove/merge/split the tags in these records. See
            <a href="https://timetagger.app/articles/tags/#manage" target='new'>this article</a> for details.<br><br>
            </p>
            <div class='formlayout'>
                <div>Tags:</div>
                <input type='text' placeholder='Tags to search for' spellcheck='false' />
                <div>Replacement:</div>
                <input type='text' placeholder='Replacement tags' spellcheck='false' />
                <div></div>
                <button type='button'>Find records</button>
                <div></div>
                <button type='button'>Replace all ...</button>
                <div></div>
                <button type='button'>Confirm</button>
                <div></div>
                <div></div>
            </div>
            <hr />
            <div class='record_grid'></div>
        """

        close_but = self.maindiv.children[0].children[-1]
        close_but.onclick = self.close

        self._records_node = self.maindiv.children[-1]

        formdiv = self.maindiv.children[2]
        self._tagname1 = formdiv.children[1]
        self._tagname2 = formdiv.children[3]
        self._button_find = formdiv.children[5]
        self._button_replace = formdiv.children[7]
        self._button_replace_comfirm = formdiv.children[9]
        self._taghelp = formdiv.children[11]

        self._tagname1.oninput = self._check_name1
        self._tagname2.oninput = self._check_names
        self._tagname1.onchange = self._fix_name1
        self._tagname2.onchange = self._fix_name2
        self._tagname1.onkeydown = self._on_key1
        self._tagname2.onkeydown = self._on_key2

        self._button_find.onclick = self._find_records
        self._button_replace.onclick = self._replace_all
        self._button_replace_comfirm.onclick = self._really_replace_all
        window._tag_manage_dialog_open_record = self._open_record

        self._button_find.disabled = True
        self._button_replace.disabled = True
        self._button_replace_comfirm.disabled = True
        self._button_replace_comfirm.style.visibility = "hidden"

        self._records_uptodate = False
        self._records = []

        super().open(None)
        if utils.looks_like_desktop():
            self._tagname1.focus()

    def close(self):
        self._records = []
        self._records_uptodate = False
        super().close()

    def _check_name1(self):
        self._records_uptodate = False
        self._check_names()

    def _check_names(self):

        name1 = self._tagname1.value
        name2 = self._tagname2.value
        tags1, _ = utils.get_tags_and_parts_from_string(name1)
        tags2, _ = utils.get_tags_and_parts_from_string(name2)

        err = ""
        ok1 = ok2 = False

        if not name1:
            pass
        elif not tags1:
            err += "Tags needs to start with '#'. "
        else:
            ok1 = True

        if not name2:
            ok2 = True  # remove is ok
        elif not tags2:
            err += "Tags needs to start with '#'. "
        else:
            ok2 = True

        self._button_find.disabled = not ok1
        self._button_replace.disabled = not (ok1 and ok2 and self._records_uptodate)
        self._button_replace_comfirm.disabled = True
        self._button_replace_comfirm.style.visibility = "hidden"
        self._taghelp.innerHTML = "<i>" + err + "</i>"

    def _fix_name1(self):
        tags1, _ = utils.get_tags_and_parts_from_string(self._tagname1.value)
        self._tagname1.value = " ".join(tags1)

    def _fix_name2(self):
        tags2, _ = utils.get_tags_and_parts_from_string(self._tagname2.value)
        self._tagname2.value = " ".join(tags2)

    def _on_key1(self, e):
        key = e.key.lower()
        if key == "enter" or key == "return":
            self._find_records()

    def _on_key2(self, e):
        key = e.key.lower()
        if key == "enter" or key == "return":
            self._replace_all()

    def _find_records(self):
        search_tags, _ = utils.get_tags_and_parts_from_string(self._tagname1.value)
        # Early exit?
        if not search_tags:
            self._records_node.innerHTML = "Nothing found."
            return
        # Get list of records
        records = []
        for record in window.store.records.get_dump():
            tags = window.store.records.tags_from_record(record)  # include #untagged
            all_ok = True
            for tag in search_tags:
                if tag not in tags:
                    all_ok = False
            if all_ok:
                records.push([record.t1, record.key])
        records.sort(key=lambda x: x[0])

        self._records = [x[1] for x in records]
        self._records_uptodate = True
        self._show_records()
        self._check_names()

    def _show_records(self):
        search_tags, _ = utils.get_tags_and_parts_from_string(self._tagname1.value)
        # Generate html
        bold_tags = [f"<b>{tag}</b>" for tag in search_tags]
        find_html = f"Finding records for tags " + ", ".join(bold_tags) + ".<br>"
        lines = [find_html, f"Found {self._records.length} records:<br>"]
        for key in self._records:
            record = window.store.records.get_by_key(key)
            ds = record.ds or ""
            date = dt.time2str(record.t1).split("T")[0]
            lines.append(
                f"""
                <a onclick='window._tag_manage_dialog_open_record("{key}")'
                    style='cursor: pointer;'>
                    <i class='fas'>\uf682</i>
                    <span>{date}</span>
                    <span>{ds}</span></a>"""
            )
        self._records_node.innerHTML = "<br />\n".join(lines)

    def _replace_all(self):
        replacement_tags, _ = utils.get_tags_and_parts_from_string(self._tagname2.value)
        n = len(self._records)
        if replacement_tags:
            text = f"Confirm replacing tags in {n} records"
        else:
            text = f"Confirm removing tags in {n} records"
        self._button_replace_comfirm.innerText = text
        self._button_replace_comfirm.disabled = False
        self._button_replace_comfirm.style.visibility = "visible"

    def _really_replace_all(self):
        search_tags, _ = utils.get_tags_and_parts_from_string(self._tagname1.value)
        replacement_tags, _ = utils.get_tags_and_parts_from_string(self._tagname2.value)

        for key in self._records:
            record = window.store.records.get_by_key(key)
            _, parts = utils.get_tags_and_parts_from_string(record.ds)
            # Get updated parts
            new_parts = []
            replacement_made = False
            for part in parts:
                if part.startswith("#") and (
                    part in search_tags or part in replacement_tags
                ):
                    if not replacement_made:
                        replacement_made = True
                        new_parts.push(" ".join(replacement_tags))
                else:
                    new_parts.push(part)
            # Submit
            record.ds = "".join(new_parts)
            window.store.records.put(record)

        self._records_node.innerHTML = ""
        self._show_records()
        self._records_uptodate = False
        self._check_names()

    def _open_record(self, key):
        record = window.store.records.get_by_key(key)
        self._canvas.record_dialog.open("Edit", record, self._show_records)


class ReportDialog(BaseDialog):
    """A dialog that shows a report of records, and allows exporting."""

    def open(self, t1, t2, tags=None):
        """Show/open the dialog ."""

        self._tags = tags or []

        # Transform time int to dates.
        t1_date = dt.time2localstr(dt.round(t1, "1D")).split(" ")[0]
        t2_date = dt.time2localstr(dt.round(t2, "1D")).split(" ")[0]
        if t1_date != t2_date:
            # The date range is inclusive (and we add 1D later): move back one day
            t2_date = dt.time2localstr(dt.add(dt.round(t2, "1D"), "-1D")).split(" ")[0]
        self._t1_date = t1_date
        self._t2_date = t2_date

        # Generate preamble
        if self._tags:
            filtertext = self._tags.join(" ")
        else:
            filtertext = "all (no tags selected)"
        self._copybuttext = "Copy table"
        html = f"""
            <h1><i class='fas'>\uf15c</i>&nbsp;&nbsp;Report
                <button type='button'><i class='fas'>\uf00d</i></button>
                </h1>
            <div class='formlayout'>
                <div>Tags:</div> <div>{filtertext}</div>
                <div>Date range:</div> <div></div>
                <div>Format:</div> <label><input type='checkbox' /> Hours in decimals</label>
                <div>Details:</div> <label><input type='checkbox' checked /> Show records</label>
                <button type='button'><i class='fas'>\uf328</i>&nbsp;&nbsp;{self._copybuttext}</button>
                    <div>to paste in a spreadsheet</div>
                <button type='button'><i class='fas'>\uf0ce</i>&nbsp;&nbsp;Save CSV</button>
                    <div>to save as spreadsheet (with more details)</div>
                <button type='button'><i class='fas'>\uf1c1</i>&nbsp;&nbsp;Save PDF</button>
                    <div>to archive or send to a client</div>
            </div>
            <hr />
            <table id='report_table'></table>
        """

        self.maindiv.innerHTML = html
        self._table_element = self.maindiv.children[-1]
        form = self.maindiv.children[1]

        # filter text = form.children[1]
        self._date_range = form.children[3]
        self._hourdecimals_but = form.children[5].children[0]  # inside label
        self._showrecords_but = form.children[7].children[0]  # inside label
        self._copy_but = form.children[8]
        self._savecsv_but = form.children[10]
        self._savepdf_but = form.children[12]

        # Connect input elements
        close_but = self.maindiv.children[0].children[-1]
        close_but.onclick = self.close
        self._date_range.innerText = t1_date + "  -  " + t2_date
        #
        self._hourdecimals_but.oninput = self._update_table
        self._showrecords_but.oninput = self._update_table
        #
        self._copy_but.onclick = self._copy_clipboard
        self._savecsv_but.onclick = self._save_as_csv
        self._savepdf_but.onclick = self._save_as_pdf

        window.setTimeout(self._update_table)
        super().open(None)

    def _update_table(self):
        t1_date = self._t1_date
        t2_date = self._t2_date
        if not float(t1_date.split("-")[0]) > 1899:
            self._table_element.innerHTML = ""
            return
        elif not float(t2_date.split("-")[0]) > 1899:
            self._table_element.innerHTML = ""
            return

        t1 = str_date_to_time_int(t1_date)
        t2 = str_date_to_time_int(t2_date)
        t2 = dt.add(t2, "1D")  # look until the end of the day

        self._last_t1, self._last_t2 = t1, t2
        html = self._generate_table_html(self._generate_table_rows(t1, t2))
        self._table_element.innerHTML = html

        # Configure the table ...
        if self._showrecords_but.checked:
            self._table_element.classList.add("darkheaders")
        else:
            self._table_element.classList.remove("darkheaders")

        # Also apply in the app itself!
        window.canvas.range.animate_range(t1, t2, None, False)  # without snap

    def _generate_table_rows(self, t1, t2):

        showrecords = self._showrecords_but.checked

        if self._hourdecimals_but.checked:
            duration2str = lambda t: f"{t / 3600:0.2f}"
        else:
            duration2str = lambda t: dt.duration_string(t, False)

        # Get stats and sorted records, this already excludes hidden records
        stats = window.store.records.get_stats(t1, t2).copy()
        records = window.store.records.get_records(t1, t2).values()
        records.sort(key=lambda record: record.t1)

        # Get better names
        name_map = utils.get_better_tag_order_from_stats(stats, self._tags, True)

        # Create list of pairs of stat-name, stat-key, and sort
        statobjects = []
        for tagz1, tagz2 in name_map.items():
            statobjects.append({"oritagz": tagz1, "tagz": tagz2, "t": stats[tagz1]})
        utils.order_stats_by_duration_and_name(statobjects)

        # Collect per tag combi, filter if necessary
        records_per_tagz = {}
        for tagz in name_map.keys():
            records_per_tagz[tagz] = []
        for i in range(len(records)):
            record = records[i]
            tags = window.store.records.tags_from_record(record)
            tagz = tags.join(" ")
            # if all([tag in tags for tag in self._tags]):
            if tagz in records_per_tagz:
                records_per_tagz[tagz].append(record)

        # Generate rows
        rows = []

        # Include total
        total = 0
        for tagz in name_map.keys():
            total += stats[tagz]
        rows.append(["head", duration2str(total), "Total", 0])

        for statobject in statobjects:
            # Add row for total of this tag combi
            duration = duration2str(statobject.t)
            pad = 1
            if showrecords:
                rows.append(["blank"])
            rows.append(["head", duration, statobject.tagz, pad])

            # Add row for each record
            if showrecords:
                records = records_per_tagz[statobject.oritagz]
                for i in range(len(records)):
                    record = records[i]
                    sd1, st1 = dt.time2localstr(record.t1).split(" ")
                    sd2, st2 = dt.time2localstr(record.t2).split(" ")
                    if True:  # st1.endsWith(":00"):
                        st1 = st1[:-3]
                    if True:  # st2.endsWith(":00"):
                        st2 = st2[:-3]
                    duration = duration2str(min(t2, record.t2) - max(t1, record.t1))
                    rows.append(
                        [
                            "record",
                            record.key,
                            duration,
                            sd1,
                            st1,
                            st2,
                            record.get("ds", ""),
                            window.store.records.tags_from_record(record).join(" "),
                        ]
                    )

        return rows

    def _generate_table_html(self, rows):
        window._open_record_dialog = self._open_record
        blank_row = "<tr class='blank_row'><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>"
        lines = []
        for row in rows:
            if row[0] == "blank":
                lines.append(blank_row)
            elif row[0] == "head":
                lines.append(
                    f"<tr><th>{row[1]}</th><th class='pad{row[3]}'>{row[2]}</th><th></th>"
                    + "<th></th><th></th><th></th><th></th></tr>"
                )
            elif row[0] == "record":
                _, key, duration, sd1, st1, st2, ds, tagz = row
                lines.append(
                    f"<tr><td></td><td></td><td>{duration}</td>"
                    + f"<td>{sd1}</td><td class='t1'>{st1}</td><td class='t2'>{st2}</td>"
                    + f"<td><a onclick='window._open_record_dialog(\"{key}\")' style='cursor:pointer;'>"
                    + f"{ds or '&nbsp;-&nbsp;'}</a></td></tr>"
                )
        return lines.join("")

    def _open_record(self, key):
        record = window.store.records.get_by_key(key)
        self._canvas.record_dialog.open("Edit", record, self._update_table)

    def _copy_clipboard(self):
        copy_dom_node(self._table_element)
        self._copy_but.innerHTML = (
            f"<i class='fas'>\uf46c</i>&nbsp;&nbsp;{self._copybuttext}"
        )
        window.setTimeout(self._reset_copy_but_text, 800)

    def _reset_copy_but_text(self):
        self._copy_but.innerHTML = (
            f"<i class='fas'>\uf328</i>&nbsp;&nbsp;{self._copybuttext}"
        )

    def _save_as_csv(self):

        rows = self._generate_table_rows(self._last_t1, self._last_t2)

        lines = []
        lines.append(
            "subtotals, tag_groups, duration, date, start, stop, description, user, tags"
        )
        lines.append("")

        user = ""  # noqa
        if window.store.get_auth:
            auth = window.store.get_auth()
            if auth:
                user = auth.email  # noqa

        for row in rows:
            if row[0] == "blank":
                lines.append(",,,,,,,,")
            elif row[0] == "head":
                lines.append(RawJS('row[1] + ", " + row[2] + ",,,,,,,"'))
            elif row[0] == "record":
                _, key, duration, sd1, st1, st2, ds, tagz = row
                ds = '"' + ds + '"'
                lines.append(
                    RawJS(
                        """',,' + duration + ', ' + sd1 + ', ' + st1 + ', ' + st2 + ', ' + ds + ', ' + user + ', ' + tagz"""
                    )
                )

        # Get blob wrapped in an object url
        obj_url = window.URL.createObjectURL(
            window.Blob(["\r\n".join(lines)], {"type": "text/csv"})
        )
        # Create a element to attach the download to
        a = document.createElement("a")
        a.style.display = "none"
        a.setAttribute("download", "timetagger-records.csv")
        a.href = obj_url
        document.body.appendChild(a)
        # Trigger the download by simulating click
        a.click()
        # Cleanup
        window.URL.revokeObjectURL(a.href)
        document.body.removeChild(a)

    def _save_as_pdf(self):

        # Configure
        width, height = 210, 297  # A4
        margin = 20  # mm
        showrecords = self._showrecords_but.checked
        rowheight = 6
        rowheight2 = rowheight / 2
        rowskip = 3
        coloffsets = 15, 4, 17, 10, 10

        # Get row data and divide in chunks. This is done so that we
        # can break pages earlier to avoid breaking chunks.
        rows = self._generate_table_rows(self._last_t1, self._last_t2)
        chunks = [[]]
        for row in rows:
            if row[0] == "blank":
                chunks.append([])
            else:
                chunks[-1].append(row)

        # Initialize the document
        doc = window.jsPDF()
        doc.setFont("Ubuntu-C")

        # Draw preamble
        doc.setFontSize(24)
        doc.text("Time record report", margin, margin, {"baseline": "top"})
        img = document.getElementById("ttlogo_bd")
        doc.addImage(img, "PNG", width - margin - 30, margin, 30, 30)
        # doc.setFontSize(12)
        # doc.text(
        #     "TimeTagger",
        #     width - margin,
        #     margin + 22,
        #     {"align": "right", "baseline": "top"},
        # )

        tagname = self._tags.join(" ") if self._tags else "all"
        d1 = reversed(dt.time2localstr(self._last_t1)[:10].split("-")).join("-")
        d2 = reversed(dt.time2localstr(self._last_t2)[:10].split("-")).join("-")
        doc.setFontSize(11)
        doc.text("Tags:  ", margin + 20, margin + 15, {"align": "right"})
        doc.text(tagname, margin + 20, margin + 15)
        doc.text("From:  ", margin + 20, margin + 20, {"align": "right"})
        doc.text(d1, margin + 20, margin + 20)
        doc.text("To:  ", margin + 20, margin + 25, {"align": "right"})
        doc.text(d2, margin + 20, margin + 25)

        # Prepare drawing table
        doc.setFontSize(10)
        left_middle = {"align": "left", "baseline": "middle"}
        right_middle = {"align": "right", "baseline": "middle"}
        y = margin + 35

        # Draw table
        npages = 1
        for chunknr in range(len(chunks)):

            # Maybe insert a page break early to preserve whole chunks
            space_used = y - margin
            space_total = height - 2 * margin
            if space_used > 0.9 * space_total:
                rowsleft = sum([len(chunk) for chunk in chunks[chunknr:]])
                space_needed = rowsleft * rowheight
                space_needed += (len(chunks) - chunknr) * rowskip
                if space_needed > space_total - space_used:
                    doc.addPage()
                    npages += 1
                    y = margin

            for rownr, row in enumerate(chunks[chunknr]):

                # Add page break?
                if (y + rowheight) > (height - margin):
                    doc.addPage()
                    npages += 1
                    y = margin

                if row[0] == "head":
                    if showrecords:
                        doc.setFillColor("#ccc")
                    else:
                        doc.setFillColor("#f3f3f3" if rownr % 2 else "#eaeaea")
                    doc.rect(margin, y, width - 2 * margin, rowheight, "F")
                    # Duration
                    doc.setTextColor("#000")
                    x = margin + coloffsets[0]
                    doc.text(row[1], x, y + rowheight2, right_middle)  # duration
                    # Tag names, add structure via color, no padding
                    basename, lastname = "", row[2]
                    doc.setTextColor("#555")
                    x += coloffsets[1]
                    doc.text(basename, x, y + rowheight2, left_middle)
                    doc.setTextColor("#000")
                    x += doc.getTextWidth(basename)
                    doc.text(lastname, x, y + rowheight2, left_middle)

                elif row[0] == "record":
                    doc.setFillColor("#f3f3f3" if rownr % 2 else "#eaeaea")
                    doc.rect(margin, y, width - 2 * margin, rowheight, "F")
                    doc.setTextColor("#000")
                    # _, key, duration, sd1, st1, st2, ds, tagz = row
                    rowvalues = row[2:]
                    # The duration is right-aligned
                    x = margin + coloffsets[0]
                    doc.text(row[2], x, y + rowheight2, right_middle)
                    # The rest is left-aligned
                    for i in range(1, 5):
                        x += coloffsets[i]
                        if i == 3:
                            doc.text("-", x - 1, y + rowheight2, right_middle)
                        doc.text(rowvalues[i], x, y + rowheight2, left_middle)

                else:
                    doc.setFillColor("#ffeeee")
                    doc.rect(margin, y, width - 2 * margin, rowheight, "F")

                y += rowheight
            y += rowskip

        # Add pagination
        doc.setFontSize(8)
        doc.setTextColor("#555")
        for i in range(npages):
            pagenr = i + 1
            doc.setPage(pagenr)
            x, y = width - 0.5 * margin, 0.5 * margin
            doc.text(f"{pagenr}/{npages}", x, y, {"align": "right", "baseline": "top"})

        doc.save("timetagger-records.pdf")
        # doc.output('dataurlnewwindow')  # handy during dev


class ExportDialog(BaseDialog):
    """Dialog to export data."""

    def __init__(self, canvas):
        super().__init__(canvas)
        self._dtformat = "local"
        self._working = 0

    def open(self, callback=None):
        self.maindiv.innerHTML = f"""
            <h1><i class='fas'>\uf56e</i>&nbsp;&nbsp;Export
                <button type='button'><i class='fas'>\uf00d</i></button>
            </h1>
            <p>
            The table below contains all your records. This can be
            useful for backups, processing, or to move your data
            elsewhere.
            </p><p>&nbsp;</p>
            <div>
                <span>Date-time format:</span>
                &nbsp;<input type="radio" name="dtformat" value="local" checked> Local</input>
                &nbsp;<input type="radio" name="dtformat" value="unix"> Unix</input>
                &nbsp;<input type="radio" name="dtformat" value="iso"> ISO 8601</input>
            </div>
            <button type='button'>Copy</button>
            <hr />
            <table id='export_table'></table>
            """

        self._table_element = self.maindiv.children[-1]
        self._table_element.classList.add("darkheaders")

        self._copy_but = self.maindiv.children[-3]
        self._copy_but.onclick = self._copy_clipboard
        self._copy_but.disabled = True

        radio_buttons = self.maindiv.children[-4].children
        for i in range(1, len(radio_buttons)):
            but = radio_buttons[i]
            but.onchange = self._on_dtformat

        self._cancel_but = self.maindiv.children[0].children[-1]
        self._cancel_but.onclick = self.close
        super().open(callback)

        self.fill_records()

    def _on_dtformat(self, e):
        self._dtformat = e.target.value
        self.fill_records()

    async def fill_records(self):
        self._working += 1
        working = self._working
        await window.stores.sleepms(100)

        # Prepare
        self._copy_but.disabled = True
        itemsdict = window.store.records._items
        lines = []

        # Add header
        lineparts = ["key", "start", "stop", "tags", "description"]
        lines.append("<tr><th>" + lineparts.join("</th><th>") + "</th></tr>")

        # Parse all items
        # Take care that description does not have newlines or tabs.
        # With tab-separated values it is not common to surround values in quotes.
        for key in itemsdict.keys():
            item = itemsdict[key]
            if not window.stores.is_hidden(item):
                t1, t2 = item.t1, item.t2
                if self._dtformat == "local":
                    t1, t2 = dt.time2localstr(t1), dt.time2localstr(t2)
                elif self._dtformat == "iso":
                    t1, t2 = dt.time2str(t1, 0), dt.time2str(t2, 0)
                lineparts = [
                    item.key,
                    t1,
                    t2,
                    utils.get_tags_and_parts_from_string(item.ds)[0].join(" "),
                    to_str(item.get("ds", "")),
                ]
                lines.append("<tr><td>" + lineparts.join("</td><td>") + "</td></tr>")
            # Give feedback while processing
            if len(lines) % 256 == 0:
                self._copy_but.innerHTML = "Found " + len(lines) + " records"
                # self._table_element.innerHTML = lines.join("\n")
                await window.stores.sleepms(1)
            if working != self._working:
                return

        # Done
        self._copy_but.innerHTML = "Copy export-table <i class='fas'>\uf0ea</i>"
        self._table_element.innerHTML = lines.join("\n")
        self._copy_but.disabled = False

    def _copy_clipboard(self):
        table = self.maindiv.children[-1]
        copy_dom_node(table)
        self._copy_but.innerHTML = "Copy export-table <i class='fas'>\uf46c</i>"
        window.setTimeout(self._reset_copy_but_text, 800)

    def _reset_copy_but_text(self):
        self._copy_but.innerHTML = "Copy export-table <i class='fas'>\uf0ea</i>"


class ImportDialog(BaseDialog):
    """Dialog to import data."""

    def __init__(self, canvas):
        super().__init__(canvas)

    def open(self, callback=None):
        self.maindiv.innerHTML = f"""
            <h1><i class='fas'>\uf56f</i>&nbsp;&nbsp;Import
                <button type='button'><i class='fas'>\uf00d</i></button>
            </h1>
            <p>
            Copy your table data (from e.g. a CSV file, a text file, or
            directly from Excel) and paste it in the text field below.
            CSV files can be dragged into the text field.
            See <a href='https://timetagger.app/articles/importing/'>this article</a>
            for details.
            </p><p>&nbsp;</p>
            <button type='button'>Analyse</button>
            <button type='button'>Import</button>
            <hr />
            <div></div>
            <textarea rows='12'
                style='background: #fff; display: block; margin: 0.5em; width: calc(100% - 1.5em);'>
            </textarea>
            """

        self._input_element = self.maindiv.children[-1]
        self._input_element.value = ""
        self._input_element.ondragexit = self._on_drop_stop
        self._input_element.ondragover = self._on_drop_over
        self._input_element.ondrop = self._on_drop

        if not (
            window.store.__name__.startswith("Demo")
            or window.store.__name__.startswith("Sandbox")
        ):
            maintext = self.maindiv.children[2]
            maintext.innerHTML += """
                Consider importing into the
                <a target='new' href='sandbox'>Sandbox</a> first.
                """

        self._analysis_out = self.maindiv.children[-2]

        self._analyse_but = self.maindiv.children[3]
        self._analyse_but.onclick = self.do_analyse
        self._import_but = self.maindiv.children[4]
        self._import_but.onclick = self.do_import
        self._import_but.disabled = True

        self._cancel_but = self.maindiv.children[0].children[-1]
        self._cancel_but.onclick = self.close
        super().open(callback)

    def _on_drop_stop(self, ev):
        self._input_element.style.background = None

    def _on_drop_over(self, ev):
        ev.preventDefault()
        self._input_element.style.background = "#DFD"

    def _on_drop(self, ev):
        ev.preventDefault()
        self._on_drop_stop()

        def apply_text(s):
            self._input_element.value = s

        if ev.dataTransfer.items:
            for i in range(len(ev.dataTransfer.items)):
                if ev.dataTransfer.items[i].kind == "file":
                    file = ev.dataTransfer.items[i].getAsFile()
                    ext = file.name.lower().split(".")[-1]
                    if ext in ("xls", "xlsx", "xlsm", "pdf"):
                        self._analysis_out.innerHTML = (
                            f"Cannot process <u>{file.name}</u>. Drop a .csv file or "
                            + f"copy the columns in Excel and paste here."
                        )
                        continue
                    reader = window.FileReader()
                    reader.onload = lambda: apply_text(reader.result)
                    reader.readAsText(file)
                    self._analysis_out.innerHTML = f"Read from <u>{file.name}</u>"
                    break  # only process first one

    async def do_analyse(self):
        """Analyze incoming data ..."""
        if self._analyzing:
            return

        # Prepare
        self._analyzing = True
        self._import_but.disabled = True
        self._import_but.innerHTML = "Import"
        self._records2import = []
        # Run
        try:
            await self._do_analyse()
        except Exception as err:
            console.warn(str(err))
        # Restore
        self._analyzing = False
        self._import_but.innerHTML = "Import"
        if len(self._records2import) > 0:
            self._import_but.disabled = False

    async def _do_analyse(self):
        global JSON

        def log(s):
            self._analysis_out.innerHTML += s + "<br />"

        # Init
        self._analysis_out.innerHTML = ""
        text = self._input_element.value.lstrip()
        header, text = text.lstrip().split("\n", 1)
        header = header.strip()
        text = text or ""

        # Parse header to get sepator
        sep, sepname, sepcount = "", "", 0
        for x, name in [("\t", "tab"), (",", "comma"), (";", "semicolon")]:
            if header.count(x) > sepcount:
                sep, sepname, sepcount = x, name, header.count(x)
        if not header:
            log("No data")
            return
        elif not sepcount or not sep:
            log("Could not determine separator (tried tab, comma, semicolon)")
            return
        else:
            log("Looks like the separator is " + sepname)

        # Get mapping to parse header names
        M = {
            "key": ["id", "identifier"],
            "projectkey": ["project key", "project id"],
            "projectname": ["project", "pr", "proj", "project name"],
            "tags": ["tags", "tag"],
            "t1": ["start", "begin", "start time", "begin time"],
            "t2": ["stop", "end", "stop time", "end time"],
            "description": ["summary", "comment", "title", "ds"],
            "projectpath": ["project path"],
            "date": [],
            "duration": [
                "duration h:m",
                "duration h:m:s",
                "duration hh:mm",
                "duration hh:mm:ss",
            ],
        }
        namemap = {}
        for key, options in M.items():
            namemap[key] = key
            for x in options:
                namemap[x] = key

        # Parse header to get names
        headerparts1 = csvsplit(header, sep)[0]
        headerparts2 = []
        headerparts_unknown = []
        for name in headerparts1:
            name = name.lower().replace("-", " ").replace("_", " ")
            if name in namemap:
                headerparts2.append(namemap[name])
            elif not name:
                headerparts2.append(None)
            else:
                headerparts_unknown.append(name)
                headerparts2.append(None)
        while headerparts2 and headerparts2[-1] is None:
            headerparts2.pop(-1)
        if headerparts_unknown:
            log("Ignoring some headers: " + headerparts_unknown.join(", "))
        else:
            log("All headers names recognized")

        # All required names headers present?
        if "t1" not in headerparts2:
            log("Missing required header for start time.")
            return
        elif "t2" not in headerparts2 and "duration" not in headerparts2:
            log("Missing required header for stop time or duration.")
            return

        # Get dict to map (t1, t2) to record key
        timemap = {}  # t1_t2 -> key
        for key, record in window.store.records._items.items():
            timemap[record.t1 + "_" + record.t2] = key

        # Now parse!
        records = []
        new_record_count = 0
        index = 0
        row = 0
        while index < len(text):
            row += 1
            try:
                # Get parts on this row
                lineparts, index = csvsplit(text, sep, index)
                if len("".join(lineparts).trim()) == 0:
                    continue  # skip empty rows
                # Build raw object
                raw = {}
                for j in range(min(len(lineparts), len(headerparts2))):
                    key = headerparts2[j]
                    if key is not None:
                        raw[key] = lineparts[j].strip()
                raw.more = lineparts[len(headerparts2) :]
                # Build record
                record = window.store.records.create(0, 0)
                record_key = None
                if raw.key:
                    record_key = raw.key  # dont store at record yet
                if True:  # raw.t1 always exists
                    record.t1 = float(raw.t1)
                    if not isFinite(record.t1):
                        record.t1 = Date(raw.t1).getTime() / 1000
                    if not isFinite(record.t1) and raw.date:
                        # Try use date, Yast uses dots, reverse if needed
                        date = raw.date.replace(".", "-")
                        if "-" in date and len(date.split("-")[-1]) == 4:
                            date = "-".join(reversed(date.split("-")))
                        tme = raw.t1
                        # Note: on IOS, Date needs to be "yyyy-mm-ddThh:mm:ss"
                        # but people are unlikely to import on an ios device ... I hope.
                        record.t1 = Date(date + " " + tme).getTime() / 1000
                    record.t1 = Math.floor(record.t1)
                if True:  # raw.t2 or duration exists -
                    record.t2 = float(raw.t2)
                    if not isFinite(record.t2):
                        record.t2 = Date(raw.t2).getTime() / 1000
                    if not isFinite(record.t2) and raw.duration:
                        # Try use duration
                        duration = float(raw.duration)
                        if ":" in raw.duration:
                            duration_parts = raw.duration.split(":")
                            if len(duration_parts) == 2:
                                duration = float(duration_parts[0]) * 3600
                                duration += float(duration_parts[1]) * 60
                            elif len(duration_parts) == 3:
                                duration = float(duration_parts[0]) * 3600
                                duration += float(duration_parts[1]) * 60
                                duration += float(duration_parts[2])
                        record.t2 = record.t1 + float(duration)
                    record.t2 = Math.ceil(record.t2)
                if raw.tags:  # If tags are given, use that
                    raw_tags = raw.tags.replace(",", " ").split()
                    tags = []
                    for tag in raw_tags:
                        tag = utils.convert_text_to_valid_tag(tag.trim())
                        if len(tag) > 2:
                            tags.push(tag)
                else:  # If no tags are given, try to derive tags from project name
                    project_name = raw.projectname or raw.projectkey or ""
                    if raw.projectpath:
                        project_parts = [raw.projectpath]
                        if raw.more and headerparts2[-1] == "projectpath":  # Yast
                            project_parts = [raw.projectpath.replace("/", " | ")]
                            for j in range(len(raw.more)):
                                if len(raw.more[j]) > 0:
                                    project_parts.append(
                                        raw.more[j].replace("/", " | ")
                                    )
                        project_parts.append(raw.projectname.replace("/", " | "))
                        project_name = "/".join(project_parts)
                    project_name = to_str(project_name)  # normalize
                    tags = []
                    if project_name:
                        tags = [utils.convert_text_to_valid_tag(project_name)]
                if True:
                    tags_dict = {}
                    for tag in tags:
                        tags_dict[tag] = tag
                    if raw.description:
                        tags, parts = utils.get_tags_and_parts_from_string(
                            raw.description
                        )
                        for tag in tags:
                            tags_dict.pop(tag, None)
                        tagz = " ".join(tags_dict.values())
                        record.ds = to_str(tagz + " " + raw.description)
                    else:
                        tagz = " ".join(tags_dict.values())
                        record.ds = tagz
                # Validate record
                if record.t1 == 0 or record.t2 == 0:
                    log(f"Item on row {row} has invalid start/stop times")
                    return
                if len(window.store.records._validate_items([record])) == 0:
                    log(
                        f"Item on row {row} does not pass validation: "
                        + JSON.stringify(record)
                    )
                    return
                record.t2 = max(record.t2, record.t1 + 1)  # no running records
                # Assign the right key based on given key or t1_t2
                if record_key is not None:
                    record.key = record_key
                else:
                    existing_key = timemap.get(record.t1 + "_" + record.t2, None)
                    if existing_key is not None:
                        record.key = existing_key
                # Add
                records.append(record)
                if window.store.records.get_by_key(record.key) is None:
                    new_record_count += 1
                # Keep giving feedback / dont freeze
                if row % 100 == 0:
                    self._import_but.innerHTML = f"Found {len(records)} records"
                    await window.stores.sleepms(1)
            except Exception as err:
                log(f"Error at row {row}: {err}")
                return

        # Store and give summary
        self._records2import = records
        log(f"Found {len(records)} ({new_record_count} new)")

    def do_import(self):
        """Do the import!"""
        window.store.records.put(*self._records2import)
        self._records2import = []
        self._import_but.disabled = True
        self._import_but.innerHTML = "Import done"


class SettingsDialog(BaseDialog):
    """Dialog to change user settings."""

    def __init__(self, canvas):
        super().__init__(canvas)

    def open(self, callback=None):

        # Get shortcuts html
        shortcuts = {
            "_dialogs": "<b>In dialogs</b>",
            "Enter": "Submit dialog",
            "Escape": "Close dialog",
            "_nav": "<b>Navigation</b>",
            "Home/End": "Snap to now (on current time-scale)",
            "d": "Select today",
            "w": "Select this week",
            "m": "Select this month",
            "↑/PageUp": "Step back in time",
            "↓/PageDown": "Step forward in time",
            "→": "Zoom in",
            "←": "Zoom out",
            "_other": "<b>Other</b>",
            "s": "Start the timer or add an earlier record",
            "x": "Stop the timer",
            "t": "Select time range",
            "r": "Open report dialog",
        }
        shortcuts_html = ""
        for key, expl in shortcuts.items():
            if key.startswith("_"):
                key = ""
            shortcuts_html += f"<div class='monospace'>{key}</div><div>{expl}</div>"

        html = f"""
            <h1><i class='fas'>\uf013</i>&nbsp;&nbsp;Settings
                <button type='button'><i class='fas'>\uf00d</i></button>
            </h1>
            <h2><i class='fas'>\uf4fd</i>&nbsp;&nbsp;Time zone</h2>
            <div></div>
            <h2><i class='fas'>\uf042</i>&nbsp;&nbsp;Dark mode</h2>
            <select>
                <option value=0>Auto detect</option>
                <option value=1>Light mode</option>
                <option value=2>Dark mode</option>
            </select>
            <h2><i class='fas'>\uf2f2</i>&nbsp;&nbsp;Show stopwatch of running record</h2>
            <label>
                <input type='checkbox' checked='true'></input>
                Show stopwatch</label>
            <h2><i class='fas'>\uf11c</i>&nbsp;&nbsp;Keyboard shortcuts</h2>
            <div class='formlayout'>{shortcuts_html}</div>
            <br /><br />
            """

        self.maindiv.innerHTML = html
        self._close_but = self.maindiv.children[0].children[-1]
        self._close_but.onclick = self.close
        (
            _,  # Dialog title
            _,  # Timezone header
            self._timezone_div,
            _,  # Darmode header
            self._darkmode_select,
            _,  # Stopwatch header
            self._stopwatch_label,
            _,  # Shortcuts header
            self._shortcuts_div,
        ) = self.maindiv.children

        # Set timezone info
        offset, offset_winter, offset_summer = dt.get_timezone_info(dt.now())
        s = f"UTC{offset:+0.2g}  /  GMT{offset_winter:+0.2g}"
        s += " summertime" if offset == offset_summer else " wintertime"
        self._timezone_div.innerText = s

        # Darkmode
        self._darkmode_select.onchange = self._on_darkmode_change
        ob = window.store.settings.get_by_key("darkmode")
        self._darkmode_select.value = 0 if ob is None else ob.value

        # Stopwatch
        self._stopwatch_check = self._stopwatch_label.children[0]
        self._stopwatch_check.onchange = self._on_stopwatch_check
        ob = window.store.settings.get_by_key("stopwatch")
        if ob is not None:
            self._stopwatch_check.checked = ob.get("value", True)

        super().open(callback)

    def _on_darkmode_change(self):
        window.select = self._darkmode_select
        mode = int(self._darkmode_select.value)
        ob = window.store.settings.create("darkmode", mode)
        window.store.settings.put(ob)
        if window.front:
            window.front.set_colors()

    def _on_stopwatch_check(self):
        stopwatch = bool(self._stopwatch_check.checked)
        ob = window.store.settings.create("stopwatch", stopwatch)
        window.store.settings.put(ob)


class InstallInstructionsDialog(BaseDialog):
    """Dialog to show install instructions."""

    def __init__(self, canvas):
        super().__init__(canvas)

    def open(self, callback=None):
        html = f"""
            <h1><i class='fas'>\uf3fa</i>&nbsp;&nbsp;How to install
                <button type='button'><i class='fas'>\uf00d</i></button>
            </h1>
            <p>
            The TimeTagger app is a Progressive Web App (PWA), which means that
            it can be installed as a native app on most devices without using
            the official appstore/playstore.
            </p><p>
            On mobile devices, the browser may prompt you with the option to
            "Add to homescreen". Otherwise, look for this option in the browser's
            menu.
            </p><p>
            On desktop, open the app in the Chrome browser and select
            "Install TimeTagger App" from the menu.
            </p>
            """

        self.maindiv.innerHTML = html

        self._cancel_but = self.maindiv.children[0].children[-1]
        self._cancel_but.onclick = self.close

        super().open(callback)
