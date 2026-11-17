# ats-strike-client

`cv`, the command-line client of [ats-strike](https://github.com/gcontini/ats-strike):
copy a job posting, get back a tailored two-page CV as a PDF. It keeps your CV
data on your machine and sends it, per request, to one or more ats-strike
servers over HTTP.

- **Using it:** [`client/README.md`](client/README.md) is the quickstart, and
  ships in every release archive. [`doc/client.md`](doc/client.md) is the full
  guide.
- **Downloading it:** the [releases page](https://github.com/gcontini/ats-strike-client/releases)
  has one archive per version, both binaries and a data folder ready to run.

## Layout

```text
client/       the CLI package (cv_client), its tests and the PyInstaller spec
contracts/    the wire format, the ats-strike-contract repository as a git submodule
examples/     a fictional candidate and a posting, for the tests and the release
doc/          the client guide, building the binary, cutting a release
```

The client imports the contracts and nothing of the server. The test that
runs the two together lives in
[ats-integration-tests](https://github.com/gcontini/ats-integration-tests).

## Developing

```bash
git clone --recurse-submodules https://github.com/gcontini/ats-strike-client
uv sync
uv run pytest            # no server, no network, no terminal
uv run cv --help
uv run --with pyinstaller pyinstaller --noconfirm client/packaging/cv.spec   # dist/cv
```

[Building the client](doc/build-client.md) and [Cutting a release](doc/release.md)
cover the rest.
