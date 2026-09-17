"""
Logging setup.

We log short, human-readable activity traces (e.g. "[AGENT] Intent: ...",
"[TOOL] Fetching historical data") so the agent's decisions are visible,
without ever printing full LLM chain-of-thought.
"""
import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:
        # Already configured (e.g. re-imported under uvicorn --reload).
        return
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%H:%M:%S"))
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
