"""cv.toml, the servers it configures, and which of them a run uses."""

from __future__ import annotations

import pytest

from cv_client.config import ConfigError, load_config

from conftest import make_server, write_cv_toml


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A folder that stands in for the current folder."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ATS_CONFIG", raising=False)
    return tmp_path


def two_servers(home, *, default="v11", extra=""):
    make_server(home, "v11")
    make_server(home, "v05")
    write_cv_toml(home, ["v11", "v05"], default=default, extra=extra)


def test_without_a_flag_only_the_default_writes(home):
    two_servers(home)
    config = load_config()
    assert [s.name for s in config.targets] == ["v11"]
    assert config.default.name == "v11"


def test_named_servers_write_and_the_default_is_still_there(home):
    two_servers(home)
    config = load_config(selected=["v05"], default_needed=True)
    assert [s.name for s in config.targets] == ["v05"]
    assert config.default.name == "v11"
    assert [s.name for s in config.servers()] == ["v05", "v11"]


def test_a_default_server_that_is_not_listed_stops_the_client(home):
    two_servers(home, default="v20")
    with pytest.raises(ConfigError, match="default_server v20: no such server"):
        load_config()


def test_the_only_server_is_the_default_without_saying_so(home):
    make_server(home, "v11")
    write_cv_toml(home, ["v11"])
    config = load_config()
    assert [s.name for s in config.targets] == ["v11"]
    assert config.default.name == "v11" and config.default.default


def test_an_unlisted_server_ver_stops_the_client(home):
    two_servers(home)
    with pytest.raises(ConfigError, match="--server_ver v20: no such server"):
        load_config(selected=["v20"])


def test_a_folder_that_is_missing_stops_the_client(home):
    make_server(home, "v11")
    write_cv_toml(home, ["v11", "v05"], default="v11")
    with pytest.raises(ConfigError, match=r"\[servers.v05\]: folder .* does not exist"):
        load_config()


@pytest.mark.parametrize("key", ["folder", "url"])
def test_a_section_without_a_folder_or_a_url_stops_the_client(home, key):
    make_server(home, "v11")
    section = {"folder": 'folder = "v11"', "url": 'url = "http://v11.invalid"'}
    del section[key]
    (home / "cv.toml").write_text("[servers.v11]\n" + "\n".join(section.values()) + "\n")
    with pytest.raises(ConfigError, match=rf"\[servers.v11\] has no {key}"):
        load_config()


def test_the_old_list_of_folders_is_refused(home):
    make_server(home, "v11")
    (home / "cv.toml").write_text('servers = ["v11"]\n')
    with pytest.raises(ConfigError, match=r"one \[servers.<name>\] section per server"):
        load_config()


def test_two_servers_may_share_a_folder_and_are_named_after_their_section(home):
    make_server(home, "v11")
    (home / "cv.toml").write_text(
        'default_server = "new"\n'
        '[servers.new]\nfolder = "v11"\nurl = "http://new.invalid"\n'
        '[servers.v05]\nfolder = "v11"\nurl = "http://old.invalid"\n'
    )
    config = load_config(selected=["v05"], default_needed=True)
    assert [(s.name, s.url, s.folder) for s in config.servers()] == [
        ("v05", "http://old.invalid", home / "v11"),
        ("new", "http://new.invalid", home / "v11"),
    ]


def test_a_mode_that_needs_the_default_stops_without_one(home):
    two_servers(home, default=None)
    with pytest.raises(ConfigError, match="no default_server is set"):
        load_config()
    with pytest.raises(ConfigError, match="no default_server is set"):
        load_config(selected=["v05"], default_needed=True)


def test_a_mode_that_names_its_server_needs_no_default(home):
    two_servers(home, default=None)
    config = load_config(selected=["v05"])
    assert [s.name for s in config.targets] == ["v05"]
    assert config.default is None


def test_no_cv_toml_says_so(home):
    with pytest.raises(ConfigError, match="no cv.toml found"):
        load_config()


def test_server_folders_are_relative_to_cv_toml(home, monkeypatch):
    data = home / "data"
    make_server(data, "v11")
    write_cv_toml(data, ["v11"])
    monkeypatch.chdir(home)

    assert load_config(data_dir=data).default.folder == data / "v11"
    assert load_config(config_file=data / "cv.toml").default.folder == data / "v11"


def test_ats_config_names_the_file(home, monkeypatch):
    data = home / "data"
    make_server(data, "v11")
    write_cv_toml(data, ["v11"])
    monkeypatch.setenv("ATS_CONFIG", str(data / "cv.toml"))
    assert load_config().config_path == data / "cv.toml"


def test_a_server_section_is_read_whole(home):
    make_server(home, "v11")
    (home / "cv.toml").write_text(
        '[servers.v11]\nfolder = "v11"\n'
        'url = "https://cv.example"\ntoken = "abc"\ntimeout = 60\n'
        "[servers.v11.settings]\npages = 2\n"
        "[servers.v11.settings.extra_body.cv]\ntemperature = 0.4\n"
    )

    server = load_config().default

    assert (server.name, server.url, server.token, server.timeout) == ("v11", "https://cv.example", "abc", 60.0)
    assert server.settings == {"pages": 2, "extra_body": {"cv": {"temperature": 0.4}}}


def test_the_command_line_beats_the_file(home):
    two_servers(home, extra='cover_letter = "yes"\n')
    assert load_config(overrides={"cover_letter": "no"}).cover_letter == "no"
    assert load_config(overrides={"cover_letter": None}).cover_letter == "yes"


def test_a_bad_cover_letter_mode_is_refused(home):
    two_servers(home)
    with pytest.raises(ConfigError, match="cover_letter"):
        load_config(overrides={"cover_letter": "maybe"})


@pytest.mark.parametrize(
    "letter, selected, lanes",
    [
        ("no", [], ["v11"]),
        ("no", ["v05"], ["v05"]),
        ("yes", ["v05"], ["v05", "v11"]),
        ("letter_only", ["v05"], ["v05", "v11"]),
        ("yes", ["v11", "v05"], ["v11", "v05"]),
    ],
)
def test_lanes_are_the_targets_and_the_default_when_it_writes_the_letter(home, letter, selected, lanes):
    two_servers(home)
    config = load_config(selected=selected, default_needed=True, overrides={"cover_letter": letter})
    assert [s.name for s in config.lanes()] == lanes


def test_server_ver_help_lists_the_configured_servers(home, capsys):
    from cv_client import cli

    two_servers(home)
    with pytest.raises(SystemExit):
        cli.main(["watch", "--help"])
    assert "Available: v11 (default), v05." in " ".join(capsys.readouterr().out.split())


def test_server_ver_help_says_when_there_are_none(home, capsys):
    from cv_client import cli

    with pytest.raises(SystemExit):
        cli.main(["render", "--help"])
    assert "Available: none (no server in cv.toml)." in " ".join(capsys.readouterr().out.split())
