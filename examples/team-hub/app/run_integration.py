#!/usr/bin/env python3
"""Run Team Hub's tests through Feature Mixer's run_tests.py and verify them.

    python3 run_integration.py

Kept from v2.0 so the old command still works. It now:
  1. runs the suite with feature-mixer/scripts/run_tests.py, which records the
     log, the per-test results, the exit code and their fingerprints in
     ../mixer/test-runs/<run-id>/ and writes the integration report from them
  2. checks the report against that evidence with verify_tests.py

The run is covered by approval A01 in ../mixer/project.json.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLE = os.path.dirname(HERE)
SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(EXAMPLE)), "feature-mixer", "scripts")
MIXER = os.path.join(EXAMPLE, "mixer")


def main():
    run = subprocess.run([sys.executable, os.path.join(SCRIPTS, "run_tests.py"), "--mixer", MIXER, "--cwd", HERE,
                          "--unittest", "tests", "--approval", "A01",
                          "--not-testable", os.path.join(MIXER, "not-testable.json")])
    if run.returncode == 2:
        return 2
    verify = subprocess.run([sys.executable, os.path.join(SCRIPTS, "verify_tests.py"), MIXER] + sys.argv[1:])
    return run.returncode or verify.returncode


if __name__ == "__main__":
    sys.exit(main())
