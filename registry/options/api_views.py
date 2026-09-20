"""Read-only lookup APIs for React data-entry forms.

Clinical vocabularies are administered through Django admin.  Entry users can
only read them here, preventing accidental creation of duplicate options.
"""

import hashlib
from typing import cast

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from rest_framework import mixins, permissions, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import models
from .serializers import build_option_serializer


OPTION_RESOURCES = {
    "centers": models.Center,
    "doctors": models.Doctor,
    "patient-types": models.PatientType,
    "districts": models.District,
    "thanas": models.Thana,
    "sexes": models.Sex,
    "economic-statuses": models.EconomicStatus,
    "blood-groups": models.BloodGroup,
    "marital-statuses": models.MaritalStatus,
    "alcohol-histories": models.AlcoholHistory,
    "smoking-histories": models.SmokingHistory,
    "tb-histories": models.TBHistory,
    "covid-histories": models.CovidHistory,
    "vaccines": models.Vaccine,
    "vaccination-doses": models.VaccinationDose,
    "diagnosis-disease-groups": models.DiagnosisDiseaseGroup,
    "diagnosis-disease-subgroups": models.DiagnosisDiseaseSubgroup,
    "diagnosis-primary-sites": models.DiagnosisPrimarySite,
    "diagnosis-metastatic-sites": models.DiagnosisMetastaticSite,
    "diagnosis-lateralities": models.DiagnosisLaterality,
    "comorbidities": models.Comorbidity,
    "histopathology-details": models.HistopathologyDetails,
    "histopathology-types": models.HistopathologyType,
    "histopathology-sites": models.HistopathologySite,
    "histopathology-grades": models.HistopathologyGrade,
    "ihc-cycles": models.IHCCycle,
    "ihc-cycle-results": models.IHCCycleResult,
    "ihc-staging-cycles": models.IHCStagingCycle,
    "ihc-staging-cycle-results": models.IHCStagingCycleResult,
    "tnm-t": models.TNMT,
    "tnm-n": models.TNMN,
    "tnm-m": models.TNMM,
    "tnm-stages": models.TNMStage,
    "molecular-methods": models.MolecularPathologyMethod,
    "molecular-specimens": models.MolecularPathologySpecimen,
    "molecular-genes": models.MolecularPathologyGene,
    "molecular-exons": models.MolecularPathologyExon,
    "molecular-alteration-types": models.MolecularAlterationType,
    "molecular-results": models.MolecularPathologyResult,
    "molecular-clinical-significances": models.MolecularClinicalSignificance,
    "molecular-panels": models.MolecularPanel,
    "molecular-panel-versions": models.MolecularPanelVersion,
    "molecular-panel-targets": models.MolecularPanelTarget,
    "cancer-marker-names": models.CancerMarkerName,
    "surgery-modalities": models.SurgeryModality,
    "surgery-lateralities": models.SurgeryLaterality,
    "radiotherapy-sites": models.RadiotherapySite,
    "radiotherapy-intents": models.RadiotherapyIntent,
    "radiotherapy-modalities": models.RadiotherapyModality,
    "treatment-modalities": models.TreatmentModality,
    "lines-of-treatment": models.LineOfTreatment,
    "treatment-protocols": models.TreatmentProtocol,
    "treatment-protocol-cycles": models.TreatmentProtocolCycleNo,
    "recist-target-lesions": models.RECISTTargetLesion,
    "recist-non-target-lesions": models.RECISTNonTargetLesion,
    "recist-new-lesions": models.RECISTNewLesion,
    "recist-response-results": models.RECISTResponseResult,
    "irecist-target-lesions": models.IRECISTTargetLesion,
    "irecist-non-target-lesions": models.IRECISTNonTargetLesion,
    "irecist-new-lesions": models.IRECISTNewLesion,
    "irecist-response-results": models.IRECISTResponseResult,
    "progression-sites": models.ProgressionSite,
    "response-estimation-methods": models.ResponseEstimationMethod,
    "pathological-response-target-lesions": models.PathologicalResponseTargetLesion,
    "pathological-response-non-target-lesions": models.PathologicalResponseNonTargetLesion,
    "pathological-response-new-lesions": models.PathologicalResponseNewLesion,
    "pathological-response-results": models.PathologicalResponseResult,
    "disease-progression-statuses": models.DiseaseProgressionStatus,
    "survival-statuses": models.SurvivalStatus,
}


class LookupPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 1000


class OptionLookupViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LookupPagination
    model: type[models.Model] | None = None
    serializer_class = None

    def get_queryset(self):
        model = self.model
        if model is None:
            raise ImproperlyConfigured("OptionLookupViewSet requires a model.")

        request = cast(Request, self.request)
        queryset = model.objects.all()
        fields = {field.name for field in model._meta.fields}
        if "name" in fields:
            queryset = queryset.order_by("name", "pk")
            search = request.query_params.get("search", "").strip()
            if search:
                queryset = queryset.filter(name__icontains=search)
        else:
            queryset = queryset.order_by("pk")

        # These dependencies drive cascading select inputs in React.
        for parameter, field in (
            ("district", "district"),
            ("gene", "gene"),
            ("marker", "marker"),
            ("protocol", "protocol"),
            ("center", "center"),
            ("doctor", "doctor"),
            ("panel", "panel"),
            ("panel_version", "panel_version"),
        ):
            if parameter in request.query_params and field in fields:
                queryset = queryset.filter(**{field: request.query_params[parameter]})
        return queryset


class OptionsCatalogAPIView(APIView):
    """Return selected lookup lists in one request for a data-entry screen."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request):
        requested = request.query_params.get("include", "")
        keys = [key.strip() for key in requested.split(",") if key.strip()] or OPTION_RESOURCES.keys()
        unknown = sorted(set(keys) - set(OPTION_RESOURCES))
        if unknown:
            return Response({"detail": "Unknown option resource.", "resources": unknown}, status=400)

        # The entry form repeats this immutable-ish vocabulary on every visit.
        # Cache by requested resource set; Django uses Redis when configured.
        digest = hashlib.sha256(",".join(keys).encode("utf-8")).hexdigest()
        catalog_version = cache.get("options-catalog:version", 0)
        cache_key = f"options-catalog:v2:{catalog_version}:{digest}"
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return Response(cached_payload)

        payload = {}
        for key in keys:
            model = OPTION_RESOURCES[key]
            queryset = model.objects.all()
            if any(field.name == "name" for field in model._meta.fields):
                queryset = queryset.order_by("name", "pk")
            payload[key] = build_option_serializer(model)(queryset, many=True).data
        cache.set(cache_key, payload, settings.OPTIONS_CATALOG_CACHE_TIMEOUT)
        return Response(payload)


class SiteSettingsAPIView(APIView):
    """Expose non-sensitive registry branding to the web client."""

    permission_classes = [permissions.AllowAny]

    def get(self, request: Request):
        settings_record = models.SiteSettings.objects.filter(pk=1).first()
        if settings_record is None:
            return Response({
                "site_title": "Lungcancer Registry",
                "header_eyebrow": "Lung Cancer Registry",
                "site_description": "",
                "logo_url": "",
                "logo_alt_text": "Lungcancer Registry logo",
                "favicon_url": "",
            })
        return Response({
            "site_title": settings_record.site_title,
            "header_eyebrow": settings_record.header_eyebrow,
            "site_description": settings_record.site_description,
            "logo_url": request.build_absolute_uri(settings_record.logo.url) if settings_record.logo else "",
            "logo_alt_text": settings_record.logo_alt_text,
            "favicon_url": request.build_absolute_uri(settings_record.favicon.url) if settings_record.favicon else "",
        })


def register_option_routes(router):
    for resource, model in OPTION_RESOURCES.items():
        viewset = type(
            f"{model.__name__}LookupViewSet",
            (OptionLookupViewSet,),
            {"model": model, "serializer_class": build_option_serializer(model)},
        )
        router.register(resource, viewset, basename=f"option-{resource}")
