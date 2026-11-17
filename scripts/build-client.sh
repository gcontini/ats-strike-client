#!/bin/sh
# Build the ats-strike client executable and install it into ats-strike-data/gab.
#
# The spec and the build command are the ones CI uses (.github/workflows/ci.yml,
# job "build"). PyInstaller does not cross-compile, so this produces a binary
# for the machine it runs on.
#
# No `uv sync` first: `uv run` syncs what it needs.
#
# Only the binary is replaced. ats-strike-data/gab also holds the user's own data
# and a cv.toml with a bearer token in it; nothing else there is touched.
set -eu

cd "$(dirname "$0")/.."

DEST="ats-strike-data/gab"

uv run --with pyinstaller pyinstaller --noconfirm --distpath build/dist --workpath build/pyinstaller_cache client/packaging/cv.spec

./build/dist/cv --help >/dev/null
./build/dist/cv version

cp build/dist/cv "$DEST/cv"
chmod +x "$DEST/cv"

# From inside the folder, so its cv.toml is the one picked up.
(cd "$DEST" && ./cv version)
