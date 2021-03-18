"""
A small set of tools for authentication, storage, and communication with the server.
Or ... the minimum tools to handle the above things.
"""

from pscript.stubs import window, JSON, localStorage, location, console, fetch


# %% General


def sleepms(ms):
    global RawJS
    return RawJS("new Promise(resolve => setTimeout(resolve, ms))")


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


def make_secure_random_string(n=8):
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    ar = window.Uint32Array(n)
    window.crypto.getRandomValues(ar)
    return "".join([chars[ar[i] % len(chars)] for i in range(n)])


def dict2url(d):
    """Encode a dict in a url-part (keys and values must be str)."""
    url = ""
    for key, val in d.items():
        assert isinstance(key, str) and isinstance(val, str)
        url += key + "=" + window.encodeURIComponent(val) + "&"
    return url


def url2dict(url):
    """Decode a dict from a url-part. Strips the "#" if present."""
    url = url.lstrip("#")
    d = {}
    for pair in url.split("&"):
        key, _, val = pair.partition("=")
        if key and val:
            d[key] = window.decodeURIComponent(val)
    return d


# %% Connecting with server


def build_api_url(suffix):
    if "/app/" in location.pathname:
        rootpath = location.pathname.split("/app/")[0]
    else:
        rootpath = location.pathname.rpartition("/")[0]
    url = location.protocol + "//" + location.hostname + ":" + location.port
    url = url.rstrip(":") + rootpath + "/api/v2/"
    return url + suffix


# %% Authentication


def get_auth_info():
    """Get the authentication info or None."""
    x = localStorage.getItem("timetagger_auth_info")
    if x:
        try:
            return JSON.parse(x)
        except Exception as err:
            console.warn("Cannot parse JSON auth info: " + str(err))
            return None
    else:
        return None


def set_auth_info_from_token(token):
    """Set the authentication by providing a TimeTagger webtoken."""
    payload_base64 = token.split(".")[1].replace("_", "/")
    auth_info = JSON.parse(
        window.decodeURIComponent(window.escape(window.atob(payload_base64)))
    )
    auth_info.token = token
    localStorage.setItem("timetagger_auth_info", JSON.stringify(auth_info))


async def logout():
    """Log the user out by discarting auth info. Await this call!"""
    # Forget the JWT and associated info.
    localStorage.removeItem("timetagger_auth_info")

    # Forget our cache. Note that this is async.
    await AsyncStorage().clear()


async def renew_webtoken(verbose=True, reset=False):
    """Renew the webtoken. Each webtoken expires after 14 days. But
    while valid, it can be exhcanged for a new one. By doing this while
    the app is active, users won't be logged out unless this device
    does not use the app for 14 days.

    If reset is True, the token seed is reset, causing all issued web
    tokens to become invalid. In other words: all sessions on other
    devices will be logged out.
    """
    auth = get_auth_info()
    if not auth:
        if verbose:
            console.warn("Could not renew token - not logged in")
        return

    url = build_api_url("webtoken")
    if reset:
        url += "?reset=1"
    init = dict(method="GET", headers={"authtoken": auth.token})
    res = await fetch(url, init)
    if res.status != 200:
        text = await res.text()
        console.warn("Could not renew token: " + text)
        if res.status == 403 and "revoked" in text:
            # When revoked, we logout to drop local changes.
            # See notes in stores.py where we do the same.
            if "/app/" in location.pathname:
                location.href = "../logout"
            else:
                location.href = "./logout"
        return

    d = JSON.parse(await res.text())
    set_auth_info_from_token(d.token)
    if verbose:
        console.warn("webtoken renewed")


# Renew token now, and set up to renew each hour
renew_webtoken()
window.setInterval(lambda: renew_webtoken(False), 60 * 60 * 1000)


# %% Storage


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
