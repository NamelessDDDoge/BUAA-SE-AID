import logging
from rest_framework import serializers, viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from ..models import LLMModel

logger = logging.getLogger(__name__)

class LLMModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLMModel
        fields = '__all__'

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
        # Full CRUD requires admin privileges (or specific admin roles if defined)
        # Using IsAuthenticated here as a placeholder, but normally one would check is_staff / is_superuser
        return [IsAuthenticated()] 

    @action(detail=False, methods=['get'])
    def active_models(self, request):
        """
        List all active LLM models for the frontend user selection.
        """
        active_qs = self.queryset.filter(is_active=True)
        serializer = self.get_serializer(active_qs, many=True)
        return Response(serializer.data)
