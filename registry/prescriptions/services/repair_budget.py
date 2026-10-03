"""Pure document repair admission accounting; reservations survive uncertain outcomes.

The workflow must persist returned state under its lease before calling a provider.
This helper alone does not activate repair or reserve a shared provider quota.
"""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


class RepairBudgetExhausted(ValueError):
    """A terminal repair exception; retain the existing usable draft."""


@dataclass(frozen=True)
class RepairLimits:
    attempts: int
    token_units: int
    seconds: int

    def __post_init__(self):
        for value in (self.attempts, self.token_units, self.seconds):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError("Repair limits must be explicitly configured positive integers.")


def reserve_repair_attempt(state, *, limits, request_sha256, input_bytes, max_output_tokens, now):
    """Return new accounting before dispatch; replay never admits a second dispatch.

    Units are conservative UTF-8 input bytes plus an output token cap, not billed
    token usage. Caller includes all prompt/schema bytes in input_bytes.
    """
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("A timezone-aware clock is required.")
    if not isinstance(request_sha256, str) or len(request_sha256) != 64 or any(c not in "0123456789abcdef" for c in request_sha256):
        raise ValueError("A verified request identity is required.")
    for value in (input_bytes, max_output_tokens):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("Complete input size and a positive output cap are required.")
    result = deepcopy(state) if state is not None else {
        "started_at": now.astimezone(timezone.utc).isoformat(),
        "deadline_at": (now + timedelta(seconds=limits.seconds)).astimezone(timezone.utc).isoformat(),
        "attempts_reserved": 0, "token_units_reserved": 0, "requests": [],
    }
    if not isinstance(result, dict) or set(result) != {"started_at", "deadline_at", "attempts_reserved", "token_units_reserved", "requests"}:
        raise ValueError("Persisted repair accounting has an invalid shape.")
    for key in ("attempts_reserved", "token_units_reserved"):
        value = result[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("Persisted repair counters must be nonnegative integers.")
    requests = result["requests"]
    if not isinstance(requests, list) or any(not isinstance(item, str) or len(item) != 64 or any(c not in "0123456789abcdef" for c in item) for item in requests) or len(set(requests)) != len(requests) or len(requests) != result["attempts_reserved"]:
        raise ValueError("Persisted repair reservations do not match their attempt counter.")
    try:
        started = datetime.fromisoformat(result["started_at"])
        stored_deadline = datetime.fromisoformat(result["deadline_at"])
    except (ValueError, TypeError):
        raise ValueError("Persisted repair clocks must be valid timestamps.") from None
    if started.utcoffset() is None or stored_deadline.utcoffset() is None or stored_deadline <= started:
        raise ValueError("Persisted repair clocks must be ordered and timezone-aware.")
    deadline = min(stored_deadline, started + timedelta(seconds=limits.seconds))
    if now < started:
        raise ValueError("Clock precedes the persisted repair budget.")
    if now >= deadline:
        raise RepairBudgetExhausted("Repair deadline exhausted.")
    if request_sha256 in result["requests"]:
        raise RepairBudgetExhausted("This repair request was already reserved; recover its audited result instead of redispatching.")
    units = input_bytes + max_output_tokens
    if result["attempts_reserved"] >= limits.attempts:
        raise RepairBudgetExhausted("Repair attempt budget exhausted.")
    if result["token_units_reserved"] + units > limits.token_units:
        raise RepairBudgetExhausted("Repair token admission budget exhausted.")
    result["deadline_at"] = deadline.isoformat()
    result["attempts_reserved"] += 1
    result["token_units_reserved"] += units
    result["requests"].append(request_sha256)
    return result
