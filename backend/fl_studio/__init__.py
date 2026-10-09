"""FL Studio 4-Layer Integration Architecture.
"""
from .bridge import FLStudioBridge, BridgeStatus
from .fl_midi_script import generate_fl_midi_script
from .automation import FLStudioUIAutomation

__all__ = ["FLStudioBridge", "BridgeStatus", "generate_fl_midi_script", "FLStudioUIAutomation"]
