"""A server: what its folder sends, and how its section is read."""

from __future__ import annotations

from cv_client.servers import read_server

from conftest import make_server


def test_the_pack_is_every_file_subfolders_included(tmp_path):
    server = make_server(tmp_path, "v11", files=("candidate_profile.json",))
    (server.folder / "cache" / "steps").mkdir(parents=True)
    (server.folder / "cache" / "steps" / "pool.json").write_bytes(b"[]")
    (server.folder / "sys_prompt_cv_body.txt").write_text("MINE")

    pack = server.pack()

    assert sorted(pack) == ["cache/steps/pool.json", "candidate_profile.json", "sys_prompt_cv_body.txt"]
    assert pack["sys_prompt_cv_body.txt"] == b"MINE"


def test_the_pack_is_read_when_asked_for(tmp_path):
    server = make_server(tmp_path, "v11", files=())
    (server.folder / "notes.md").write_text("one")
    first = server.pack()
    (server.folder / "notes.md").write_text("two")
    assert (first["notes.md"], server.pack()["notes.md"]) == (b"one", b"two")


def test_a_server_is_named_after_its_section_not_its_folder(tmp_path):
    make_server(tmp_path, "v11")
    server = read_server(tmp_path, "v05", {"folder": "v11", "url": "http://v05.invalid"})
    assert (server.name, server.folder, server.default, server.timeout, server.settings) == (
        "v05",
        tmp_path / "v11",
        False,
        1800.0,
        {},
    )
