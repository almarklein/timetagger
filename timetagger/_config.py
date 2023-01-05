import os
import sys


def to_bool(value):
    """Converts a string to a bool"""
    stringValue = str(value).lower()
    if stringValue in ["true", "yes", "on", "1"]:
        return True
    return False


class Config:
    """Object that holds config values.

    * `bind (str)`: the address and port to bind on. Default "0.0.0.0:80".
    * `datadir (str)`: the directory to store data. Default "~/_timetagger".
      The user db's are stored in `datadir/users`.
    * `log_level (str)`: the log level for timetagger and asgineer
      (not the asgi server). Default "info".
    * `credentials (str)`: login credentials for one or more users, in the
      form "user1:hash1,user2:hash2" where each hash is a salted hash (BCrypt)
      of the password. Used in the default startup script ``__main__.py``.
      You can generate credentials with https://timetagger.app/cred.
    * `proxy_auth_enabled (bool)`: enables authentication from a reverse proxy
      (for example Authelia). Default "False".
    * `proxy_auth_trusted (str)`: list of trusted reverse proxy IPs with or without CIDR, in the
      form "127.0.0.1,10.0.0.1,10.99.0.0/24,192.168/16". Default "127.0.0.1".
    * `proxy_auth_header (str)`: name of the proxy header which contains the
      username of the logged in user. Default "X-Remote-User".

    The values can be configured using CLI arguments and environment variables.
    For CLI arguments, the following formats are supported:
    ```
    python -m timetagger --datadir=~/timedata
    python -m timetagger --datadir ~/timedata
    ```

    For environment variable, the key is uppercase and prefixed:
    ```
    TIMETAGGER_DATADIR=~/timedata
    ```
    """

    _ITEMS = [
        ("bind", str, "0.0.0.0:80"),
        ("datadir", str, "~/_timetagger"),
        ("log_level", str, "info"),
        ("credentials", str, ""),
        ("proxy_auth_enabled", to_bool, False),
        ("proxy_auth_trusted", str, "127.0.0.1"),
        ("proxy_auth_header", str, "X-Remote-User"),
    ]
    __slots__ = [name for name, _, _ in _ITEMS]


config = Config()


def set_config(argv=None, env=None):
    """Set config values. By default argv is sys.argv and env is os.environ."""
    if argv is None:
        argv = sys.argv
    if env is None:
        env = os.environ

    _reset_config_to_defaults()
    _update_config_from_argv(argv)
    _update_config_from_env(env)


def _reset_config_to_defaults():
    for name, _, default in Config._ITEMS:
        setattr(config, name, default)


def _update_config_from_argv(argv):

    for i in range(len(argv)):
        arg = argv[i]
        for name, conv, _ in Config._ITEMS:
            if arg.startswith(f"--{name}="):
                _, _, raw_value = arg.partition("=")
            elif arg == f"--{name}":
                if i + 1 < len(argv):
                    raw_value = argv[i + 1]
                else:
                    raise RuntimeError(f"Value for {arg} not given")
            else:
                continue
            try:
                setattr(config, name, conv(raw_value))
            except Exception as err:
                raise RuntimeError(f"Could not set config.{name}: {err}")
            break


def _update_config_from_env(env):

    for name, conv, _ in Config._ITEMS:
        env_name = f"TIMETAGGER_{name.upper()}"
        raw_value = env.get(env_name, None)
        if raw_value:
            try:
                setattr(config, name, conv(raw_value))
            except Exception as err:
                raise RuntimeError(f"Could not set config.{name}: {err}")


# Init config
set_config()
