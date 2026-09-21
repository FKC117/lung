"""Analysis-time PFS and OS calculation helpers; no durations are persisted."""

from records.models import DiseaseProgressionRecord, SurvivalFollowUp


def calculate_pfs(treatment_course):
    """Return the earliest progression/death event, or last survival follow-up censor date."""
    index_date = treatment_course.started_on
    if index_date is None:
        raise ValueError("A treatment course start date is required to calculate PFS.")

    patient = treatment_course.observation.patient
    progression_date = (
        DiseaseProgressionRecord.objects.filter(
            observation__patient=patient,
            status__code="progressed",
            progression_date__isnull=False,
            progression_date__gte=index_date,
        )
        .order_by("progression_date")
        .values_list("progression_date", flat=True)
        .first()
    )
    death_date = (
        SurvivalFollowUp.objects.filter(
            observation__patient=patient,
            status__code="dead",
            death_date__isnull=False,
            death_date__gte=index_date,
        )
        .order_by("death_date")
        .values_list("death_date", flat=True)
        .first()
    )
    events = [("progression", progression_date), ("death", death_date)]
    event, event_date = min((item for item in events if item[1]), key=lambda item: item[1], default=(None, None))
    censor_date = None
    if event_date is None:
        censor_date = (
            SurvivalFollowUp.objects.filter(observation__patient=patient, followed_up_on__gte=index_date)
            .order_by("-followed_up_on")
            .values_list("followed_up_on", flat=True)
            .first()
        )
    end_date = event_date or censor_date
    return {"event": event, "event_date": event_date, "censored_on": censor_date, "duration_days": (end_date - index_date).days if end_date else None}


def calculate_os(observation, index_date):
    """Return death event or last follow-up censor date from a supplied OS index date."""
    patient = observation.patient
    death_date = (
        SurvivalFollowUp.objects.filter(observation__patient=patient, status__code="dead", death_date__isnull=False, death_date__gte=index_date)
        .order_by("death_date").values_list("death_date", flat=True).first()
    )
    censor_date = None
    if death_date is None:
        censor_date = (
            SurvivalFollowUp.objects.filter(observation__patient=patient, followed_up_on__gte=index_date)
            .order_by("-followed_up_on").values_list("followed_up_on", flat=True).first()
        )
    end_date = death_date or censor_date
    return {"event": "death" if death_date else None, "event_date": death_date, "censored_on": censor_date, "duration_days": (end_date - index_date).days if end_date else None}
