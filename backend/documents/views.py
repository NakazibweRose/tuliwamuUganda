from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from audit.services import record
from cases import access
from core.permissions import IsInstitutionalUser
from institutions.models import Institution
from referrals.models import Referral

from . import services
from .models import DocumentCategory


class DocumentSerializer(serializers.Serializer):
    def to_representation(self, d):
        user = self.context["request"].user
        inst = user.institution
        own = d.institution_id == inst.id
        return {
            "id": str(d.id), "case_id": str(d.case_id), "case_reference": d.case.reference,
            "referral": {"id": str(d.referral_id), "reference": d.referral.reference, "category": d.referral.category} if d.referral_id else None,
            "category": d.category, "title": d.title, "filename": d.filename, "mime_type": d.mime_type, "size_bytes": d.size_bytes,
            "institution": {"id": str(d.institution_id), "name": d.institution.name},
            "uploaded_by": d.uploaded_by.display_name(), "created_at": d.created_at,
            "forwardable": d.forwardable, "is_own": own,
            # Only the owner sees the full sharing list (who else holds a copy).
            "shared_with": [a.institution.name for a in d.access.select_related("institution")] if own else None,
            "can_forward": own or d.forwardable,
        }


class UploadThrottle(UserRateThrottle):
    scope = "document_upload"
    rate = "60/hour"

    def allow_request(self, request, view):
        return True if request.method == "GET" else super().allow_request(request, view)


class DocumentViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Need-to-know case documents. Admins, complainants and caregivers are refused by IsInstitutionalUser."""

    permission_classes = [IsInstitutionalUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = DocumentSerializer
    throttle_classes = [UploadThrottle]

    def get_queryset(self):
        qs = services.visible_documents(self.request.user)
        if self.request.query_params.get("case"):
            qs = qs.filter(case_id=self.request.query_params["case"])
        if self.request.query_params.get("referral"):
            from django.db.models import Q

            rid = self.request.query_params["referral"]
            # Files uploaded on this referral, plus files forwarded between the two parties via it.
            # (qs already contains only documents this institution may read.)
            qs = qs.filter(Q(referral_id=rid) | Q(access__via_referral_id=rid)).distinct()
        return qs

    def list(self, request):
        qs = self.get_queryset()
        return Response(DocumentSerializer(qs, many=True, context={"request": request}).data)

    def create(self, request):
        category = request.data.get("category")
        if category not in DocumentCategory.values:
            return Response({"error": {"code": "validation_error", "message": "Choose a document type.", "details": {"category": ["Choose a document type."]}}}, status=400)
        referral = None
        if request.data.get("referral_id"):
            referral = get_object_or_404(Referral.objects.select_related("case"), pk=request.data["referral_id"])
            case = referral.case
            inst = request.user.institution
            if inst.id not in (referral.sending_institution_id, referral.receiving_institution_id):
                return Response({"error": {"code": "not_found", "message": "Not found.", "details": None}}, status=404)
        else:
            case = get_object_or_404(access.team_cases(request.user), pk=request.data.get("case_id"))
        forwardable = str(request.data.get("forwardable", "true")).lower() in {"1", "true", "yes", "on"}
        doc = services.upload(request.user, case, request.FILES.get("file"), category, request.data.get("title", ""),
                              referral=referral, forwardable=forwardable, request=request)
        return Response(DocumentSerializer(doc, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        doc = self.get_object()
        raw = services.decrypt(doc)
        if raw is None:
            return Response({"error": {"code": "unavailable", "message": "File unavailable.", "details": None}}, status=410)
        record(request.user, "document.download", doc, request=request, case_id=str(doc.case_id), security=True)
        resp = HttpResponse(raw, content_type=doc.mime_type)
        resp["Content-Disposition"] = f'attachment; filename="{doc.filename}"'
        resp["Cache-Control"] = "no-store, private"
        resp["X-Content-Type-Options"] = "nosniff"
        resp["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return resp

    @action(detail=True, methods=["get"], url_path="share-targets")
    def share_targets(self, request, pk=None):
        doc = self.get_object()
        return Response([{"id": str(i.id), "name": i.name, "type": i.type} for i in services.share_targets(request.user, doc)])

    @action(detail=True, methods=["post"])
    def share(self, request, pk=None):
        doc = self.get_object()
        target = get_object_or_404(Institution, pk=request.data.get("institution_id"))
        services.share(request.user, doc, target, request=request)
        return Response(DocumentSerializer(doc, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        doc = self.get_object()
        services.withdraw(request.user, doc, request.data.get("reason", ""), request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)
