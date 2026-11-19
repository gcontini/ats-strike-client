"""The servers a CV is written with: one ``[servers.<name>]`` section each in ``cv.toml``.

A section says where the server is and which of its pipelines to ask — one
``url``, ``http://host/v1`` — its token, its timeout, the
``[settings]`` table forwarded to it untouched, and the folder that holds everything it is
sent: your candidate files, any prompt, template or image you want instead of
its own, and a ``cache/`` it fills itself. The client reads no file name in
that folder: what the files mean is the server's business. Two sections may
share a folder.

A server's name is its section's name: the name ``--server_ver`` takes, the
suffix its PDFs get and the job sub-folder it stores in. The default server,
named by ``default_server`` in ``cv.toml``, analyses every posting and writes
the cover letter; the others only write CVs. With one server configured, that
is the default.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

#: How long to follow a CV job before giving up on it, by default.
DEFAULT_TIMEOUT = 1800.0


class ConfigError(RuntimeError):
    """The configuration cannot produce a working client."""


@dataclass(frozen=True)
class Server:
    """One ``[servers.<name>]`` section of ``cv.toml``."""

    name: str
    folder: Path
    #: The server and its pipeline: ``http://host/v1``.
    url: str
    token: Optional[str] = None
    #: Analyses postings and writes the letter: ``default_server`` in ``cv.toml``.
    default: bool = False
    #: Seconds to follow one CV job.
    timeout: float = DEFAULT_TIMEOUT
    #: ``[settings]``: sent with every request as it is; its meaning is the server's.
    settings: Mapping[str, Any] = field(default_factory=dict)

    def pack(self) -> Dict[str, bytes]:
        """Every file under the folder, read now, by its path relative to the
        folder with ``/``."""
        files: Dict[str, bytes] = {}
        for path in sorted(self.folder.rglob("*")):
            if path.is_file():
                files[path.relative_to(self.folder).as_posix()] = path.read_bytes()
        return files


def read_server(base: Path, name: str, raw: Any) -> Server:
    """The server one section describes; its folder is relative to ``base``."""
    if not isinstance(raw, dict):
        raise ConfigError(f"servers.{name} must be a [servers.{name}] section")
    for key in ("folder", "url"):
        if not raw.get(key):
            raise ConfigError(f"[servers.{name}] has no {key}")
    folder = (base / raw["folder"]).resolve()
    if not folder.is_dir():
        raise ConfigError(f"[servers.{name}]: folder {folder} does not exist")
    return Server(
        name=name,
        folder=folder,
        url=raw["url"],
        token=raw.get("token") or None,
        timeout=float(raw.get("timeout", DEFAULT_TIMEOUT)),
        settings=dict(raw.get("settings") or {}),
    )


def load_servers(
    base: Path,
    sections: Any,
    *,
    default: Optional[str] = None,
    selected: Sequence[str] = (),
    default_needed: bool = False,
) -> Tuple[Tuple[Server, ...], Optional[Server]]:
    """The servers this run writes CVs with, and the default.

    ``sections`` is the ``servers`` table of ``cv.toml``, one section per
    server: each is read now, used or not. ``default`` is the section name
    ``default_server`` gives; with one server configured it may be left out.
    ``selected`` are the ``--server_ver`` names; without any, the default is
    the one target. ``default_needed`` is for the modes that analyse postings,
    which the default does whatever the targets are.
    """
    if not isinstance(sections, dict):
        raise ConfigError("servers must be one [servers.<name>] section per server")
    by_name = {name: read_server(base, name, raw) for name, raw in sections.items()}
    if default is None and len(by_name) == 1:
        default = next(iter(by_name))
    default_server = None
    if default is not None:
        if default not in by_name:
            raise ConfigError(f"default_server {default}: no such server (configured: {', '.join(by_name) or 'none'})")
        default_server = by_name[default] = replace(by_name[default], default=True)
    for name in selected:
        if name not in by_name:
            raise ConfigError(f"--server_ver {name}: no such server (configured: {', '.join(by_name) or 'none'})")
    if default_server is None and (default_needed or not selected):
        raise ConfigError(
            "no default_server is set in cv.toml" + ("" if by_name else " (no server is configured at all)")
        )
    targets = tuple(by_name[name] for name in selected) if selected else (default_server,)
    return targets, default_server


__all__ = ["Server", "ConfigError", "DEFAULT_TIMEOUT", "read_server", "load_servers"]
