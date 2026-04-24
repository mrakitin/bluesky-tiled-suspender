# bluesky-tiled-suspender

An [ophyd](https://blueskyproject.io/ophyd/) signal and [bluesky](https://blueskyproject.io/bluesky/) suspender that monitors the health of a [Tiled](https://blueskyproject.io/tiled/) server and automatically pauses a `RunEngine` when the server is not ready.

## Overview

- **`TiledHealthSignal`** — an `ophyd.Signal` subclass that polls a Tiled `/healthz` endpoint and exposes the `"status"` string (e.g. `"ready"`). Returns `"offline"` on any network or parsing error.
- **`tiled_status`** — a pre-built instance pointed at `https://tiled.nsls2.bnl.gov/healthz`.
- **`TiledSuspender`** — a `bluesky.suspenders.SuspenderBase` subclass that suspends the `RunEngine` whenever the signal value is not `"ready"` and resumes once it returns to `"ready"`.

## Quick start

```python
from bluesky import RunEngine
from tiled_suspender import tiled_status, TiledSuspender

RE = RunEngine()
RE.install_suspender(TiledSuspender(tiled_status))
```

To target a different Tiled instance:

```python
from tiled_suspender import TiledHealthSignal, TiledSuspender

my_status = TiledHealthSignal(name="my_tiled", url="https://my-tiled-server/healthz")
suspender = TiledSuspender(my_status)
RE.install_suspender(suspender)
```

## Installation

Dependencies are managed with [pixi](https://pixi.sh):

```bash
pixi install          # default environment (ophyd, bluesky, requests)
pixi install -e dev   # dev environment (adds pytest)
```

## Running tests

```bash
# Unit tests only (no network required)
pixi run -e dev test

# Include the live-endpoint integration test
pixi run -e dev test-network
```
