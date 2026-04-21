from ..models import Log


def log_user_event(*, user, operation_type, related_model, related_id):
    return Log.objects.create(
        user=user,
        operation_type=operation_type,
        related_model=related_model,
        related_id=related_id,
    )
