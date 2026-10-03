from datetime import datetime, timedelta, timezone
from copy import deepcopy
from django.test import SimpleTestCase
from prescriptions.services.repair_budget import RepairLimits, RepairBudgetExhausted, reserve_repair_attempt


class TargetedRepairBudgetTests(SimpleTestCase):
    def setUp(self):
        self.now = datetime(2020, 1, 1, tzinfo=timezone.utc)
        self.limits = RepairLimits(attempts=1, token_units=1000, seconds=60)

    def reserve(self, state=None, **changes):
        return reserve_repair_attempt(state, **{
            "limits": self.limits, "request_sha256": "a" * 64,
            "input_bytes": 100, "max_output_tokens": 200, "now": self.now, **changes,
        })

    def test_reservation_is_observable_and_does_not_mutate_saved_state(self):
        first = self.reserve()
        before = deepcopy(first)
        second = self.reserve(first, limits=RepairLimits(2, 1000, 60), request_sha256="b" * 64)
        self.assertEqual(first, before)
        self.assertEqual(second["attempts_reserved"], 2)
        self.assertEqual(second["token_units_reserved"], 600)

    def test_attempts_replays_and_uncertain_outcomes_cannot_redispatch(self):
        first = self.reserve()
        for changes in ({}, {"request_sha256": "b" * 64}):
            with self.assertRaises(RepairBudgetExhausted):
                self.reserve(first, **changes)

    def test_input_and_output_both_count_and_exhaustion_preserves_state(self):
        first = self.reserve()
        before = deepcopy(first)
        with self.assertRaises(RepairBudgetExhausted):
            self.reserve(first, limits=RepairLimits(2, 500, 60), request_sha256="b" * 64)
        self.assertEqual(first, before)
        with self.assertRaises(RepairBudgetExhausted):
            self.reserve(input_bytes=900)

    def test_deadline_boundary_and_configuration_changes_cannot_extend_budget(self):
        first = self.reserve()
        with self.assertRaises(RepairBudgetExhausted):
            self.reserve(first, limits=RepairLimits(2, 1000, 600), request_sha256="b" * 64, now=self.now + timedelta(seconds=60))
        with self.assertRaises(RepairBudgetExhausted):
            self.reserve(first, limits=RepairLimits(2, 1000, 10), request_sha256="b" * 64, now=self.now + timedelta(seconds=10))
        with self.assertRaises(ValueError):
            self.reserve(first, now=self.now - timedelta(seconds=1))

    def test_missing_zero_negative_boolean_limits_and_naive_clock_fail(self):
        for value in (0, -1, True, "1"):
            with self.assertRaises(ValueError):
                RepairLimits(value, 1000, 60)
            with self.assertRaises(ValueError):
                self.reserve(max_output_tokens=value)
        for identity in (None, "", "z" * 64):
            with self.assertRaises(ValueError):
                self.reserve(request_sha256=identity)
        with self.assertRaises(ValueError):
            self.reserve(now=self.now.replace(tzinfo=None))

    def test_corrupt_saved_accounting_fails_closed_without_resetting_limits(self):
        first = self.reserve()
        for changes in ({"attempts_reserved": -1}, {"token_units_reserved": -100},
                        {"attempts_reserved": True}, {"requests": []},
                        {"requests": ["a" * 64, "a" * 64]},
                        {"started_at": "bad"}, {"deadline_at": "2020-01-01T00:01:00"},
                        {"deadline_at": first["started_at"]}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.reserve({**first, **changes})
        for state in ({}, [], {**first, "extra": 1}):
            with self.assertRaises(ValueError):
                self.reserve(state)
