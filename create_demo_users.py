import os
import sys
from datetime import timedelta
from pathlib import Path

import django


BACKEND_ROOT = Path(__file__).resolve().parent / "ai-forensics" / "code" / "backend" / "backend-code"
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fake_image_detector.settings")
django.setup()

from django.utils import timezone

from core.models import InvitationCode, Organization, User


def upsert_user(email, username, password, role, organization=None, *, is_staff=False, is_superuser=False):
    user, _ = User.objects.get_or_create(email=email, defaults={"username": username})
    user.username = username
    user.role = role
    user.organization = organization
    user.is_staff = is_staff
    user.is_superuser = is_superuser
    user.set_password(password)
    user.save()
    return user


org, _ = Organization.objects.get_or_create(
    name="DemoOrganization",
    defaults={
        "email": "demo@organization.com",
        "description": "Local demo organization",
        "remaining_non_llm_uses": 100,
        "remaining_llm_uses": 3,
    },
)

admin = upsert_user(
    "admin_demo@example.com",
    "admin_demo",
    "AdminDemo123!",
    "admin",
    is_staff=True,
    is_superuser=True,
)
publisher = upsert_user(
    "publisher_demo@example.com",
    "publisher_demo",
    "PublisherDemo123!",
    "publisher",
    organization=org,
)
reviewer = upsert_user(
    "reviewer_demo@example.com",
    "reviewer_demo",
    "ReviewerDemo123!",
    "reviewer",
    organization=org,
)

if org.admin_user_id != admin.id:
    org.admin_user = admin
    org.save(update_fields=["admin_user"])

for code, role in (("pub1234", "publisher"), ("rev1234", "reviewer")):
    InvitationCode.objects.update_or_create(
        code=code,
        defaults={
            "organization": org,
            "role": role,
            "is_used": False,
            "expires_at": timezone.now() + timedelta(days=30),
        },
    )

print(f"organization: {org.name} (id={org.id})")
print(f"admin: {admin.email} / AdminDemo123!")
print(f"publisher: {publisher.email} / PublisherDemo123!")
print(f"reviewer: {reviewer.email} / ReviewerDemo123!")
print("admin endpoint: /api/admin-login/")
print("user endpoint: /api/login/ with role=publisher or reviewer")
