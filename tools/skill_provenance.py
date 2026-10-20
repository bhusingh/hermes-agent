"""Skill write-origin provenance: a ContextVar separating background-review skill writes from foreground
user-directed writes (the curator only curates skills the self-improvement review fork created; skills a user
asked for belong to the user). run_agent.py binds the origin before each tool loop, mirroring
AIAgent._memory_write_origin: ``token = set_current_write_origin(...)`` / ``reset_current_write_origin(token)``."""

import contextvars
import json
from typing import Any

_write_origin: contextvars.ContextVar[str] = contextvars.ContextVar("skill_write_origin", default="foreground")
BACKGROUND_REVIEW = "background_review"  # sentinel used by run_agent._spawn_background_review


def set_current_write_origin(origin: str) -> contextvars.Token[str]:
    return _write_origin.set(origin or "foreground")


def reset_current_write_origin(token: contextvars.Token[str]) -> None:
    _write_origin.reset(token)


def get_current_write_origin() -> str:
    """"foreground" for any regular agent (CLI, gateway, cron, subagent); "background_review" for the review fork."""
    return _write_origin.get()


def is_background_review() -> bool:
    return get_current_write_origin() == BACKGROUND_REVIEW


# Attendedness is orthogonal to origin: an explicit ``/refine`` fork IS a background review (every
# curator / skill-ledger / approval guard keyed on ``is_background_review()`` must still apply), but a
# user asked for it, so the unattended-only memory delete gate (#105921) does not.
_review_attended: contextvars.ContextVar[bool] = contextvars.ContextVar("review_attended", default=False)


def set_review_attended(attended: bool) -> contextvars.Token[bool]:
    return _review_attended.set(bool(attended))


def reset_review_attended(token: contextvars.Token[bool]) -> None:
    _review_attended.reset(token)


def is_unattended_review() -> bool:
    return is_background_review() and not _review_attended.get()


# Source references for a memory/skill write (which documents, reviews or runs a lesson came from). Callers
# that drive writes programmatically bind it around the call; the write-approval gate stores it in the pending
# record and the skill ledger stores it as evidence, so a change can later be traced to (and removed with) its
# sources. Agent-supplied tool arguments never set it.
_write_provenance: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "write_provenance", default=None)


def set_write_provenance(meta: dict[str, Any] | None) -> contextvars.Token:
    """Bind source metadata (a JSON-serializable dict, or None) for writes in this context."""
    if meta is not None:
        if not isinstance(meta, dict):
            raise TypeError("write provenance must be a dict")
        meta = json.loads(json.dumps(meta))  # JSON-only copy: later caller mutations cannot leak in
    return _write_provenance.set(meta or None)


def reset_write_provenance(token: contextvars.Token) -> None:
    _write_provenance.reset(token)


def get_write_provenance() -> dict[str, Any] | None:
    return _write_provenance.get()
