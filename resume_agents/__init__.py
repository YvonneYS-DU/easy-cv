"""
resume_agents — multi-agent resume system.

Built on the agi_agents LangChain wrapper.
"""

import os
import sys

# Ensure agi_agents llm_wrapper is importable (lazy; avoid pulling fitz etc. at import time)
_agi_agents_path = os.path.join(os.path.dirname(__file__), "..", "..", "agi_agents")
if os.path.exists(_agi_agents_path) and _agi_agents_path not in sys.path:
    sys.path.insert(0, _agi_agents_path)

from resume_agents.orchestrator import ResumeOrchestrator
from resume_agents.memory.models import (
    MaterialRecord,
    MaterialContent,
    Resume,
    ResumeSection,
    JDMatchResult,
)
from resume_agents.memory.store import MaterialStore
from resume_agents.domain.profiles import get_domain, list_domains

__all__ = [
    "ResumeOrchestrator",
    "MaterialRecord",
    "MaterialContent",
    "Resume",
    "ResumeSection",
    "JDMatchResult",
    "MaterialStore",
    "get_domain",
    "list_domains",
]
