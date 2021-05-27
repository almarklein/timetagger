"""
Misc utils.
"""

import os
import json
import secrets
from base64 import urlsafe_b64encode, urlsafe_b64decode

import jwt


ROOT_TT_DIR = os.path.expanduser("~/_timetagger")
ROOT_USER_DIR = os.path.join(ROOT_TT_DIR, "users")
if not os.path.isdir(ROOT_USER_DIR):
    os.makedirs(ROOT_USER_DIR)


# %% Username stuff

ok_chars = frozenset("-_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")


def user2filename(username):
    """Convert a username (e.g. email address) to the corresponding absolute filename."""
    # The rules for characters in email addresses are quite complex,
    # but can at least contain !#$%&'*+-/=?^_`{|}~. Therefore we
    # agressively create a clean representation (for recognizability)
    # and a base64 encoded string (so that we can reverse this process).

    clean = "".join((c if c in ok_chars else "-") for c in username)
    encoded = urlsafe_b64encode(username.encode()).decode()
    fname = clean + "~" + encoded + ".db"

    return os.path.join(ROOT_USER_DIR, fname)


def filename2user(filename):
    """Convert a (relative or absolute) filename to the corresponding username."""
    fname = os.path.basename(filename)
    encoded = fname.split("~")[-1].split(".")[0]
    return urlsafe_b64decode(encoded.encode()).decode()


# %% JWT


def _load_jwt_key():
    """Load the secret JWT key from file. If it does not exist, we
    simply create a new one. This means that by removing this key file
    and restarting the server, all issued tokens before that time will
    become invalid.
    """
    filename = os.path.join(ROOT_TT_DIR, "jwt.key")
    secret = ""
    if os.path.isfile(filename):
        with open(filename, "rb") as f:
            secret = f.read().decode().strip()
    if not secret:
        secret = secrets.token_urlsafe(32)
        with open(filename, "wb") as f:
            f.write(secret.encode())
    return secret


JWT_KEY = _load_jwt_key()


def create_jwt(payload):
    """Create a new JWT with the given payload."""
    for key in ("username", "expires", "seed"):
        if key not in payload:
            raise ValueError(f"JWT must have a {key} field.")
    result = jwt.encode(payload, JWT_KEY, algorithm="HS256")
    if isinstance(result, bytes):
        return result.decode()
    return result


def decode_jwt(token):
    """Decode a JWT, validating it with our key. Returns the payload as a dict."""
    return jwt.decode(token, JWT_KEY, algorithms=["HS256"])


def decode_jwt_nocheck(token):
    """Get the payload (as a dict) from a JWT token without performing
    any validating.
    """
    payload_b64 = token.split(".")[1]
    missing_padding = len(payload_b64) % 4
    if missing_padding:
        payload_b64 += "=" * missing_padding
    payload_s = urlsafe_b64decode(payload_b64.encode()).decode()
    return json.loads(payload_s)


# %% Very basic SCSS parser


def get_scss_vars(text):
    """Get scss variables from a source file. These can then be supplied
    to compile_scss_to_css() when parsing other scss files.
    """
    vars = {}
    for line in text.splitlines():
        if line.lstrip().startswith("$") and ":" in line and line.endswith(";"):
            name, _, val = line.partition(":")
            name, val = name.strip(), val.strip().strip(";").strip()
            vars[name] = val
    return vars


def compile_scss_to_css(text, **extra_vars):
    """Very basic scss compiler that can only replace $variables. But
    that's enough for now. Yes, I know pyScss, but it produces loads
    of warnings which I find annoying.
    """
    # Get complete vars
    vars = {}
    for key, val in extra_vars.items():
        if not key.startswith("$"):
            key = "$" + key
        vars[key] = val
    vars.update(get_scss_vars(text))
    # Pre-process
    lines = text.splitlines()
    lines2remove = []
    for i in range(len(lines)):
        line = lines[i]
        if line.lstrip().startswith("$") and ":" in line:
            lines2remove.append(i)
            lines[i] = ""
    text = "\n".join(lines)
    # Sort keys by length to avoid replacing partial keys
    var_keys = list(vars.keys())
    var_keys.sort(key=lambda x: len(x), reverse=True)
    # Replace in vars themselves
    for key in var_keys:
        val = vars[key]
        for k, v in vars.items():
            if key in v:
                vars[k] = v.replace(key, val)
    # Replace in text
    for key in var_keys:
        val = vars[key]
        text = text.replace(key, val)
    # Post-check
    lines = text.splitlines()
    for i in range(len(lines)):
        line = lines[i]
        if "$" in line:
            raise ValueError(f"Found unreplaced SCSS variable on line {i+1}:\n{line}")
    for i in reversed(lines2remove):
        lines.pop(i)
    return "\n".join(lines)
