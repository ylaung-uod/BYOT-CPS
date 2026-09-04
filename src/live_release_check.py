#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

from gns3_api import GNS3API

ROOT = Path(__file__).resolve().parents[1]
SMOKE_COUNTS = (0, 1, 3, 10)
SMOKE_PREFIX = "byot-cps-smoke-"


def smoke_projects(api):
    return sorted(
        project["name"]
        for project in api.get("/projects")
        if project["name"].startswith(SMOKE_PREFIX)
    )


def run(api, counts=SMOKE_COUNTS, command_runner=subprocess.run):
    existing = smoke_projects(api)
    if existing:
        raise SystemExit(f"refusing to start with temporary projects present: {existing}")

    for count in counts:
        environment = os.environ.copy()
        environment["COMPROMISED_IOT_COUNT"] = str(count)
        print(f"live release gate: compromised-IoT count={count}", flush=True)
        try:
            command_runner(
                [sys.executable, str(ROOT / "src" / "smoke_test.py")],
                cwd=ROOT,
                env=environment,
                check=True,
            )
        finally:
            leftovers = smoke_projects(api)
            if leftovers:
                raise RuntimeError(
                    f"temporary projects remain after count {count}: {leftovers}"
                )

    print("LIVE GNS3 RELEASE CHECK: PASSED (counts 0, 1, 3, 10; no temporary projects remain)")


def main():
    run(GNS3API())


if __name__ == "__main__":
    main()
