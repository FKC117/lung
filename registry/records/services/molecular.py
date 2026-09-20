from django.core.exceptions import ValidationError
from django.db import transaction

from options.models import (
    MolecularPanelTarget,
    MolecularPanelVersion,
    MolecularPathologyResult,
)
from records.models import MolecularTest, MolecularTestResult


@transaction.atomic
def finalize_molecular_test(test_id):
    molecular_test = (
        MolecularTest.objects
        .select_for_update()
        .select_related("panel_version")
        .get(pk=test_id)
    )

    if molecular_test.status == MolecularTest.Status.COMPLETED:
        return {
            "test": molecular_test,
            "created_negatives": 0,
            "already_completed": True,
        }

    if molecular_test.status in {
        MolecularTest.Status.FAILED,
        MolecularTest.Status.CANCELLED,
    }:
        raise ValidationError(
            "Failed or cancelled molecular tests cannot be finalized."
        )

    panel_version = molecular_test.panel_version
    if panel_version is None:
        raise ValidationError(
            "A panel version is required before finalization."
        )

    if molecular_test.qc_status != MolecularTest.QCStatus.PASSED:
        raise ValidationError(
            "QC must pass before the test can be finalized."
        )

    targets = list(
        MolecularPanelTarget.objects
        .filter(panel_version=panel_version, is_reportable=True)
        .select_related("gene", "alteration_type")
        .prefetch_related("covered_exons")
    )

    if not targets:
        raise ValidationError(
            "The selected panel version has no reportable targets."
        )

    # Connect manually entered results to their matching panel target.
    existing_results = list(
        MolecularTestResult.objects
        .filter(molecular_test=molecular_test)
        .select_for_update()
        .select_related(
            "panel_target",
            "gene",
            "exon",
            "alteration_type",
        )
    )

    target_lookup = {
        (target.gene, target.alteration_type): target
        for target in targets
    }

    for result in existing_results:
        if result.panel_target is not None:
            if result.panel_target.panel_version != panel_version:
                raise ValidationError(
                    "A result is linked to a target from another panel version."
                )
            continue

        target = target_lookup.get(
            (result.gene, result.alteration_type)
        )

        if not target:
            raise ValidationError(
                f"{result.gene} / {result.alteration_type} "
                "is not covered by this panel version."
            )

        if result.exon is not None:
            covered_exons = set(target.covered_exons.all())

            if covered_exons and result.exon not in covered_exons:
                raise ValidationError(
                    f"{result.exon} is not covered by target {target}."
                )

        result.panel_target = target
        result.save(update_fields=["panel_target"])

    created_negatives = 0

    if (
        panel_version.reporting_policy
        == MolecularPanelVersion.ReportingPolicy.UNREPORTED_NEGATIVE
    ):
        not_detected = MolecularPathologyResult.objects.get(
            code="not_detected"
        )

        existing_targets = {
            result.panel_target
            for result in (
                MolecularTestResult.objects
                .filter(molecular_test=molecular_test)
                .exclude(panel_target__isnull=True)
                .select_related("panel_target")
            )
            if result.panel_target is not None
        }

        negative_results = []

        for target in targets:
            if target in existing_targets:
                continue

            negative_results.append(
                MolecularTestResult(
                    molecular_test=molecular_test,
                    panel_target=target,
                    gene=target.gene,
                    alteration_type=target.alteration_type,
                    result=not_detected,
                    origin=MolecularTestResult.Origin.DERIVED,
                    notes="Automatically derived during panel finalization.",
                )
            )

        MolecularTestResult.objects.bulk_create(negative_results)
        created_negatives = len(negative_results)

    molecular_test.status = MolecularTest.Status.COMPLETED
    molecular_test.save(update_fields=["status"])

    return {
        "test": molecular_test,
        "created_negatives": created_negatives,
        "already_completed": False,
    }
