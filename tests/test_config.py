from _common import run_tests
from pytest import raises

from timetagger import config
from timetagger._config import set_config


def test_config():
    # Defaults
    default_bind = "127.0.0.1:8080"
    set_config([], {})
    assert config.bind == default_bind
    assert config.datadir == "~/_timetagger"

    # argv
    set_config(["--bind=localhost:8080"], {})
    assert config.bind == "localhost:8080"
    set_config(["foobar.py", "--bind=localhost:8081", "-v", "--spam=eggs"], {})
    assert config.bind == "localhost:8081"
    set_config(["foobar.py", "--bind", "localhost:8082", "-v", "--spam", "eggs"], {})
    assert config.bind == "localhost:8082"

    # argv fails
    set_config(["bind=localhost:8080"], {})
    assert config.bind == default_bind
    set_config(["-bind=localhost:8080"], {})
    assert config.bind == default_bind
    with raises(RuntimeError):
        set_config(["foobar.py", "--bind"], {})

    # env
    set_config([], {"TIMETAGGER_BIND": "localhost:8081"})
    assert config.bind == "localhost:8081"

    # env fails
    set_config([], {"BIND": "localhost:8080"})
    assert config.bind == default_bind
    set_config([], {"timetagger_bind": "localhost:8080"})
    assert config.bind == default_bind

    # Test integer conv - disabled because all our config values are str
    # set_config([], {})
    # assert config.test == 3
    # set_config(["--test=42"], {})
    # assert config.test == 42
    # set_config([], {"TIMETAGGER_TEST": "7"})
    # assert config.test == 7
    # with raises(RuntimeError):
    #     set_config(["--test=notanumber"], {})
    # with raises(RuntimeError):
    #     set_config([], {"TIMETAGGER_TEST": "notanumber"})

    # Test path_prefix configuration
    set_config([], {})
    assert config.path_prefix == "/timetagger/"
    set_config(["--path_prefix=/custom/"], {})
    assert config.path_prefix == "/custom/"
    set_config(["--path_prefix=custom"], {})
    assert config.path_prefix == "/custom/"
    set_config(["--path_prefix=/custom"], {})
    assert config.path_prefix == "/custom/"
    set_config(["--path_prefix=custom/path"], {})
    assert config.path_prefix == "/custom/path/"
    set_config(["--path_prefix=/"], {})
    assert config.path_prefix == "/"
    set_config([], {"TIMETAGGER_PATH_PREFIX": "/api/"})
    assert config.path_prefix == "/api/"
    set_config([], {"TIMETAGGER_PATH_PREFIX": "api"})
    assert config.path_prefix == "/api/"

    # Test app_redirect configuration
    set_config([], {})
    assert config.app_redirect is False
    set_config(["--app_redirect=true"], {})
    assert config.app_redirect is True
    set_config(["--app_redirect=1"], {})
    assert config.app_redirect is True
    set_config(["--app_redirect=yes"], {})
    assert config.app_redirect is True
    set_config(["--app_redirect=false"], {})
    assert config.app_redirect is False
    set_config(["--app_redirect=0"], {})
    assert config.app_redirect is False
    set_config(["--app_redirect=no"], {})
    assert config.app_redirect is False
    set_config([], {"TIMETAGGER_APP_REDIRECT": "true"})
    assert config.app_redirect is True
    set_config([], {"TIMETAGGER_APP_REDIRECT": "false"})
    assert config.app_redirect is False

    # Reset to normal (using sys.argv and os.environ)
    set_config()


if __name__ == "__main__":
    run_tests(globals())
