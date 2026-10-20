"""Child-only lease clock seam; retain the rehearsal's network fence.

The real OS lock must reject entry before logical time advances. No admission,
issuance, session, or error-classification code is replaced.
"""

from pathlib import Path
import runpy
import sys

tests = Path(__file__).resolve().parents[2]
runpy.run_path(str(tests / "rehearsal" / "sitecustomize.py"))
sys.path.insert(0, str(tests.parent))

from lib import acquisition as acq  # noqa: E402
from lib.sources.net import WalkDeadline  # noqa: E402

now = [0.0]
acq.WalkDeadline = lambda budget: WalkDeadline(budget, clock=lambda: now[0])
enter = acq.DestinationLease.__enter__


def enter_and_spend_wait(self):
    try:
        return enter(self)
    except acq.AcquisitionError as error:
        if error.reason == "breaker_open":
            now[0] += 1000.0
        raise


acq.DestinationLease.__enter__ = enter_and_spend_wait
