"""The client's own settings, and the servers ``cv.toml`` configures.

``cv.toml`` holds the client's settings and one section per server::

    default_server = "v11"
    cover_letter   = "no"           # "no" | "yes" | "letter_only"
    verbose        = false

    [servers.v11]
    folder = "v11"                  # relative to this file
    url    = "https://..."

See :mod:`.servers` for what a section holds. A flag beats ``cv.toml``.
Nothing here reads the network or the job folders.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .servers import ConfigError, Server, load_servers

#: What --cover-letter accepts.
COVER_LETTER_MODES = ("no", "yes", "letter_only")

CONFIG_NAME = "cv.toml"


@dataclass(frozen=True)
class Config:
    """Everything a mode needs to know before it starts."""

    #: The servers that write CVs this run: the ``--server_ver`` ones, else the default.
    targets: Tuple[Server, ...] = ()
    #: The server that analyses postings and writes the letter.
    default: Optional[Server] = None
    cover_letter: str = "no"
    #: --verbose: print what the server reports about each step, and its log lines.
    verbose: bool = False
    #: Where the config came from, for the messages that mention it.
    config_path: Optional[Path] = None

    def servers(self) -> List[Server]:
        """Every server this run talks to: the targets, then the default, each once."""
        found = list(self.targets)
        if self.default is not None and self.default not in found:
            found.append(self.default)
        return found

    def lanes(self) -> List[Server]:
        """One CV queue each: every target, and the default when a letter is
        asked for and it is not a target."""
        lanes = list(self.targets)
        if self.cover_letter != "no" and self.default is not None and self.default not in lanes:
            lanes.append(self.default)
        return lanes


def find_config(explicit: Optional[Path] = None, data_dir: Optional[Path] = None) -> Optional[Path]:
    """Locate ``cv.toml``: the flag, then ``$ATS_CONFIG``, then the data folder
    (``--data-dir``, else the current folder)."""
    if explicit is not None:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"config file not found: {path}")
        return path
    from_env = os.getenv("ATS_CONFIG")
    if from_env:
        path = Path(from_env).expanduser()
        if path.is_file():
            return path
    candidate = Path(data_dir or Path.cwd()).expanduser() / CONFIG_NAME
    return candidate if candidate.is_file() else None


def server_names(config_file: Optional[Path] = None,
                 data_dir: Optional[Path] = None) -> Tuple[List[str], Optional[str]]:
    """The ``[servers.<name>]`` sections of ``cv.toml`` and the default's name,
    for the help text: nothing is checked, and a file that cannot be read gives
    none."""
    try:
        path = find_config(config_file, data_dir)
        raw = tomllib.loads(path.read_text(encoding="utf-8")) if path else {}
    except (OSError, tomllib.TOMLDecodeError):
        return [], None
    sections = raw.get("servers")
    names = list(sections) if isinstance(sections, dict) else []
    default = raw.get("default_server") or (names[0] if len(names) == 1 else None)
    return names, default


def load_config(
    *,
    config_file: Optional[Path] = None,
    data_dir: Optional[Path] = None,
    selected: Sequence[str] = (),
    default_needed: bool = False,
    overrides: Optional[Dict[str, Any]] = None,
) -> Config:
    """Build the :class:`Config` for this run.

    ``selected`` and ``default_needed`` are handed to
    :func:`~.servers.load_servers`. ``overrides`` holds the command-line values
    (``None`` where the flag was not given), so they are applied last and win.
    """
    path = find_config(config_file, data_dir)
    raw: Dict[str, Any] = {}
    if path is not None:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))

    config = Config(
        cover_letter=raw.get("cover_letter", Config.cover_letter),
        verbose=bool(raw.get("verbose", Config.verbose)),
        config_path=path,
    )
    cli_changes = {k: v for k, v in (overrides or {}).items() if v is not None}
    config = replace(config, **cli_changes)
    if config.cover_letter not in COVER_LETTER_MODES:
        raise ConfigError(
            f"cover_letter must be one of {', '.join(COVER_LETTER_MODES)}; "
            f"got {config.cover_letter!r}"
        )

    base = path.parent if path is not None else Path.cwd()
    try:
        targets, default = load_servers(base, raw.get("servers", {}),
                                        default=raw.get("default_server"), selected=selected,
                                        default_needed=default_needed)
    except ConfigError as exc:
        where = path or f"no {CONFIG_NAME} found"
        raise ConfigError(f"{where}: {exc}") from exc
    return replace(config, targets=targets, default=default)


__all__ = ["Config", "ConfigError", "load_config", "find_config", "server_names",
           "COVER_LETTER_MODES", "CONFIG_NAME"]
