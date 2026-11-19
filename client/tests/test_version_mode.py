"""``cv version``: the build, and whether each server is one it can talk to."""

from __future__ import annotations

from dataclasses import replace

import httpx

from cv_client import __version__
from cv_client import cli
from cv_client.api import HttpApi
from cv_client.modes import version as version_mode

from conftest import make_server, write_cv_toml


def _server(protocol: int) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "request_id": "r1",
                "ok": True,
                "data": {
                    "status": "ok",
                    "version": "1.1.0",
                    "protocol": protocol,
                    "pdflatex": True,
                    "models": {},
                    "auth_required": False,
                },
            },
        )

    return httpx.Client(transport=httpx.MockTransport(handler), base_url="http://server.invalid")


def _serving(monkeypatch, protocols: dict) -> None:
    """Each server URL answers /healthz with its own protocol."""
    real = HttpApi
    monkeypatch.setattr(
        version_mode, "HttpApi", lambda url, token=None: real(url, token=token, client=_server(protocols[url]))
    )


def test_a_server_on_this_protocol_is_reported_and_exits_zero(monkeypatch, capsys, config):
    _serving(monkeypatch, {"http://v11.invalid": 2})
    assert version_mode.run(config) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == f"version {__version__}"
    assert out[1].startswith("server v11: v1.1.0 at http://v11.invalid")
    assert "speaks this client's protocol" in out[1]


def test_each_selected_server_is_checked_and_another_protocol_exits_one(monkeypatch, capsys, config, servers_dir):
    v05 = make_server(servers_dir, "v05")
    _serving(monkeypatch, {"http://v11.invalid": 2, "http://v05.invalid": 1})

    assert version_mode.run(replace(config, targets=(config.default, v05))) == 1

    out = capsys.readouterr().out.splitlines()
    assert "speaks this client's protocol" in out[1]
    assert out[2].startswith("server v05:") and "speaks protocol 1" in out[2]
    assert "refuses to talk to it" in out[2]


def test_cv_version_checks_every_server_cv_toml_lists(tmp_path, monkeypatch, capsys):
    for name in ("v11", "v05", "v20"):
        make_server(tmp_path, name)
    write_cv_toml(tmp_path, ["v11", "v05", "v20"], default="v11")
    monkeypatch.delenv("ATS_CONFIG", raising=False)
    _serving(monkeypatch, {"http://v11.invalid": 2, "http://v05.invalid": 1, "http://v20.invalid": 2})

    assert cli.main(["version", "--data-dir", str(tmp_path)]) == 1

    out = capsys.readouterr().out.splitlines()
    assert out[0] == f"version {__version__}"
    assert [line.split(":")[0] for line in out[1:]] == ["server v11", "server v05", "server v20"]


def test_an_unreachable_server_is_not_a_failure(monkeypatch, capsys, config):
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    down = httpx.Client(transport=httpx.MockTransport(refuse), base_url="http://server.invalid")
    monkeypatch.setattr(version_mode, "HttpApi", lambda url, token=None: HttpApi(url, token=token, client=down))

    assert version_mode.run(config) == 0

    out = capsys.readouterr().out.splitlines()
    assert out[0] == f"version {__version__}"
    assert out[1].startswith("server v11: not checked")


def test_a_broken_cv_toml_does_not_stop_the_answer(tmp_path, capsys):
    broken = tmp_path / "cv.toml"
    broken.write_text("= broken [")
    assert cli.main(["version", "--config", str(broken)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == f"version {__version__}"
    assert out[1].startswith("server: not checked")


def test_an_unlisted_default_does_not_stop_the_answer_either(tmp_path, monkeypatch, capsys):
    make_server(tmp_path, "v11")
    make_server(tmp_path, "v05")
    write_cv_toml(tmp_path, ["v11", "v05"], default="v20")
    monkeypatch.delenv("ATS_CONFIG", raising=False)

    assert cli.main(["version", "--data-dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == f"version {__version__}"
    assert "default_server v20: no such server" in out[1]
