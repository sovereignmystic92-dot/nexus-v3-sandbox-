"""Host entry point for post-analysis research, with passive interactive intake."""

from .research_loop import require, run_research


def dispatch_research(binding, research, save, read, *, trigger, is_due, max_steps=5):
    """Continue a queued mission only on a trusted manual or scheduled trigger.

    The host owns durable queueing, due-time calculation, and trigger identity.
    Research checkpoints use the existing controller's readback contract.
    """
    require(trigger in ("interactive", "manual", "schedule"))
    require(type(is_due) is bool)
    if trigger == "interactive":
        return {"status": "DEFERRED_TO_QUEUE", "state": None}
    if trigger == "schedule" and not is_due:
        return {"status": "NOT_DUE", "state": None}
    return run_research(binding, research, save, read, max_steps=max_steps)
