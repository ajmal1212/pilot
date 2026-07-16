"""Production process-manager backends and their shared machinery.

The dev foreground runner, ProcessDefinition and the ProcessManager constructors
live one level up in pilot.managers.processes.local. This package holds only
the production side: base.py (ManagedProcessManager + UnitGroup), renderers.py (config
text builders), and one module per backend (systemd/supervisor).
"""

from __future__ import annotations

from pilot.managers.processes.base import ManagedProcessManager, UnitGroup

__all__ = ["ManagedProcessManager", "UnitGroup"]
