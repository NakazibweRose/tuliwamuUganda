from rest_framework import serializers

from .models import Institution


class InstitutionSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Institution
        fields = ["id", "name", "type", "district", "region", "public_contact", "is_demo", "is_active", "member_count"]
