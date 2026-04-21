# utils/serializers_safe.py
from django.db.models.fields.files import FieldFile

def serialize_value(value, request):
    """
    - File/ImageField → 完整 URL
    - 其他 → 原样返回（必须是 JSON 可序列化的原生类型）
    """
    if isinstance(value, FieldFile):
        return value.url if value and value.url else None
    return value
