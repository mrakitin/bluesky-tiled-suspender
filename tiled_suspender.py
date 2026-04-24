"""
Tiled health signal and bluesky suspender.

Exposes the health status of a Tiled server (via its /healthz endpoint) as an
ophyd Signal, and provides a bluesky Suspender that pauses a RunEngine whenever
the server is not ready.

Typical usage::

    from bluesky import RunEngine
    from tiled_suspender import tiled_status, TiledSuspender

    RE = RunEngine()
    suspender = TiledSuspender(tiled_status)
    RE.install_suspender(suspender)
"""

from abc import abstractmethod

import requests
from ophyd import Signal
from ophyd.utils.errors import ReadOnlyError
from bluesky.suspenders import SuspenderBase


class TiledHealthSignal(Signal):
    """An ophyd Signal that reads the health status of a Tiled server.

    Fetches ``GET <url>`` on every :meth:`get` call and returns the value of
    the ``"status"`` key from the JSON response (e.g. ``"ready"``).  Returns
    ``"offline"`` on any network or parsing error.

    Parameters
    ----------
    url : str
        The Tiled ``/healthz`` endpoint URL.
    timeout : float
        HTTP request timeout in seconds.
    *args, **kwargs
        Forwarded to :class:`ophyd.Signal`.
    """

    def __init__(
        self,
        *args,
        url: str = "https://tiled.nsls2.bnl.gov/healthz",
        timeout: float = 5.0,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._url = url
        self._timeout = timeout

    def get(self) -> str:
        """Fetch the current Tiled health status.

        Returns
        -------
        str
            ``"ready"`` when the server is healthy, or ``"offline"`` when the
            server cannot be reached or returns an unexpected response.
        """
        try:
            response = requests.get(self._url, timeout=self._timeout)
            response.raise_for_status()
            status = response.json().get("status", "unknown")
        except Exception:
            status = "offline"
        self._readback = status
        return status

    def put(self, value, **kwargs):
        raise ReadOnlyError(f"{self.name} is a read-only signal.")


# Pre-built instance ready to use
tiled_status = TiledHealthSignal(name="tiled_status")


class TiledSuspender(SuspenderBase):
    """A bluesky suspender that pauses a RunEngine when Tiled is not ready.

    The RunEngine is suspended whenever the watched signal value is anything
    other than ``"ready"``, and resumes once the value returns to ``"ready"``.

    Parameters
    ----------
    signal : ophyd.Signal
        The signal to watch.  Defaults to the module-level
        :obj:`tiled_status` instance.
    sleep : float
        Seconds to wait after the resume condition is met before releasing
        the suspension.
    *args, **kwargs
        Forwarded to :class:`bluesky.suspenders.SuspenderBase`.

    Examples
    --------
    >>> from bluesky import RunEngine
    >>> from tiled_suspender import tiled_status, TiledSuspender
    >>> RE = RunEngine()
    >>> suspender = TiledSuspender(tiled_status)
    >>> RE.install_suspender(suspender)
    """

    def __init__(self, signal=None, *, sleep: float = 0, **kwargs):
        if signal is None:
            signal = tiled_status
        super().__init__(signal, sleep=sleep, **kwargs)

    def _should_suspend(self, value) -> bool:
        return value != "ready"

    def _should_resume(self, value) -> bool:
        return value == "ready"


if __name__ == "__main__":
    from bluesky import RunEngine
    import bluesky.plans as bp

    print(f"Tiled status: {tiled_status.get()!r}")

    RE = RunEngine()
    suspender = TiledSuspender(tiled_status)
    RE.install_suspender(suspender)
    print(f"Suspender installed: {suspender!r}")
    print("RunEngine will suspend whenever tiled_status != 'ready'.")
