import logging
from rest_framework import serializers, viewsets
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from ..models import LLMModel

logger = logging.getLogger(__name__)

class LLMModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLMModel
        fields = (
            'id',
            'model_name',
            'display_name',
            'provider',
            'model_type',
            'endpoint',
            'api_key',
            'has_api_key',
            'is_active',
            'description',
            'health_status',
            'health_detail',
            'health_checked_at',
            'credit_used',
            'credit_total',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'has_api_key', 'health_status', 'health_detail', 'health_checked_at',
            'credit_used', 'credit_total', 'created_at', 'updated_at',
        )
        extra_kwargs = {
            'api_key': {'write_only': True, 'required': False, 'allow_blank': True, 'allow_null': True},
        }

    has_api_key = serializers.SerializerMethodField()

    def get_has_api_key(self, obj):
        return bool((obj.api_key or '').strip())

    def validate(self, attrs):
        model_type = attrs.get('model_type') or getattr(self.instance, 'model_type', 'chat')
        if model_type not in {'chat', 'fastdetect'}:
            raise serializers.ValidationError({'model_type': 'Invalid model_type'})
        return attrs

    def create(self, validated_data):
        validated_data['api_key'] = (validated_data.get('api_key') or '').strip()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'api_key' in validated_data:
            next_key = (validated_data.get('api_key') or '').strip()
            if next_key:
                validated_data['api_key'] = next_key
            else:
                validated_data.pop('api_key', None)
        return super().update(instance, validated_data)


class IsSoftwareAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.email == 'admin@mail.com' or (user.is_staff and user.organization is None))
        )


class LLMModelViewSet(viewsets.ModelViewSet):
    """
    CRUD API for LLM Models (For Admins)
    And a list of active models (For normal users)
    """
    queryset = LLMModel.objects.all().order_by('-created_at')
    serializer_class = LLMModelSerializer

    def get_permissions(self):
        if self.action in ['active_models']:
            return [IsAuthenticated()]
        return [IsSoftwareAdmin()]

    @action(detail=False, methods=['get'])
    def active_models(self, request):
        """
        List all active LLM models for the frontend user selection.
        """
        active_qs = self.queryset.filter(is_active=True, model_type='chat')
        serializer = self.get_serializer(active_qs, many=True)
        return Response(serializer.data)
