from importlib.metadata import version

try:
    __version__ = version("task-messager")
except Exception:
    __version__ = "0.2.X"

from .core import DOMAINS, app
from .logger import setup_logging
from .models import AnalysisStep, Domain, SendMessageInput, SendMessageResult, SolutionStep

__all__ = [
    "DOMAINS",
    "AnalysisStep",
    "Domain",
    "SendMessageInput",
    "SendMessageResult",
    "SolutionStep",
    "app",
    "setup_logging",
]
