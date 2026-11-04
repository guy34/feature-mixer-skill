#!/usr/bin/env python3
"""Check a Feature Mixer feature menu for broken picks.

Usage:
    python3 check_menu.py mixer/feature-menu.csv

This is the v1 command, kept so existing scripts and habits keep working.
Since v2 it runs the full validator (validate_feature_menu.py), which adds
duplicate-id, circular and transitive dependency, merge-group, evidence and
strategy checks to the original dependency and conflict checks. It accepts
the same options as validate_feature_menu.py.

Exits 0 when the picks are consistent, 1 when anything needs fixing,
2 on a bad file. Standard library only, no network.
"""

import sys

from validate_feature_menu import check, load, main, validate  # noqa: F401

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
