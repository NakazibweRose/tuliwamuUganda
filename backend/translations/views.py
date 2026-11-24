from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .catalog import coverage


@api_view(["GET"])
@permission_classes([AllowAny])
def translation_status(request):
    """Which backend message catalogues are reviewed. Used to show a 'draft translation' notice."""
    return Response(coverage())
