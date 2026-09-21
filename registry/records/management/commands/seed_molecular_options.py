from django.core.management.base import BaseCommand, CommandError

from options.models import (
    MolecularAlterationType,
    MolecularPanel,
    MolecularPanelTarget,
    MolecularPanelVersion,
    MolecularPathologyExon,
    MolecularPathologyGene,
    MolecularPathologyMethod,
    MolecularPathologyResult,
)


class Command(BaseCommand):
    help = "Create the baseline lung molecular panel and result vocabulary."

    def handle(self, *args, **options):
        ngs, _ = MolecularPathologyMethod.objects.get_or_create(name="NGS")
        panel, _ = MolecularPanel.objects.get_or_create(
            name="Lung Cancer Core Panel",
            defaults={"description": "Baseline targeted lung cancer molecular panel."},
        )
        panel_version, _ = MolecularPanelVersion.objects.get_or_create(
            panel=panel,
            version="1.0",
            defaults={
                "method": ngs,
                "reporting_policy": MolecularPanelVersion.ReportingPolicy.UNREPORTED_NEGATIVE,
            },
        )

        snv, _ = MolecularAlterationType.objects.get_or_create(name="SNV/Indel")
        fusion, _ = MolecularAlterationType.objects.get_or_create(name="Fusion")
        amplification, _ = MolecularAlterationType.objects.get_or_create(name="Amplification")

        genes = {
            name: MolecularPathologyGene.objects.get_or_create(name=name)[0]
            for name in ("EGFR", "ALK", "ROS1", "RET", "MET")
        }
        egfr_exons = [
            MolecularPathologyExon.objects.get_or_create(gene=genes["EGFR"], name=exon)[0]
            for exon in ("18", "19", "20", "21")
        ]
        met_exons = [
            MolecularPathologyExon.objects.get_or_create(gene=genes["MET"], name="14")[0]
        ]

        targets = {
            "egfr": (genes["EGFR"], snv, egfr_exons),
            "alk": (genes["ALK"], fusion, []),
            "ros1": (genes["ROS1"], fusion, []),
            "ret": (genes["RET"], fusion, []),
            "met-snv": (genes["MET"], snv, met_exons),
            "met-amplification": (genes["MET"], amplification, []),
        }
        for gene, alteration_type, exons in targets.values():
            target, _ = MolecularPanelTarget.objects.get_or_create(
                panel_version=panel_version,
                gene=gene,
                alteration_type=alteration_type,
            )
            if exons:
                target.covered_exons.set(exons)

        for code, name in (("not_detected", "Not detected"), ("detected", "Detected")):
            self._ensure_result(code, name)

        self.stdout.write(self.style.SUCCESS(f"Seeded molecular panel: {panel_version}"))

    @staticmethod
    def _ensure_result(code, name):
        """Reuse legacy result rows identified by name and normalize their code."""
        by_code = MolecularPathologyResult.objects.filter(code=code).first()
        by_name = MolecularPathologyResult.objects.filter(name=name).first()

        if by_code and by_name and by_code.pk != by_name.pk:
            raise CommandError(
                f"Conflicting molecular results exist for code '{code}' and name '{name}'."
            )

        result = by_code or by_name
        if result is None:
            MolecularPathologyResult.objects.create(code=code, name=name)
        elif result.code != code:
            result.code = code
            result.save(update_fields=["code"])
