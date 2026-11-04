"""Team Hub: tasks, approvals, comments, notifications and a workload dashboard.

Built by Feature Mixer from three sources: TaskBoard (A), Approvals (B) and
Pulse (C). See ../../mixer for how each part was chosen and designed.
"""

from . import approvals  # noqa: F401  (registers the approval status guard on tasks)

__version__ = "1.0.0"
