from django.core.management.base import BaseCommand
from core.models import Organization, User


class Command(BaseCommand):
    help = 'Seed local database with default accounts for testing'

    def handle(self, *args, **options):
        PASSWORD = '123456'

        # 软件超级管理员
        admin, created = User.objects.get_or_create(
            email='admin@mail.com',
            defaults={
                'username': 'admin',
                'role': 'admin',
                'is_superuser': True,
                'is_staff': True,
                'permission': 1111,
            }
        )
        if created or not admin.check_password(PASSWORD):
            admin.set_password(PASSWORD)
            admin.save()
        self.stdout.write(f"{'Created' if created else 'Exists'}: admin@mail.com (superuser)")

        # IEEE 组织
        org, _ = Organization.objects.get_or_create(
            name='IEEE',
            defaults={'email': 'ieee@ieee.org'}
        )

        # IEEE 组织管理员
        manager, created = User.objects.get_or_create(
            email='manager@mail.com',
            defaults={
                'username': 'manager',
                'role': 'admin',
                'organization': org,
                'permission': 1111,
            }
        )
        if created or not manager.check_password(PASSWORD):
            manager.set_password(PASSWORD)
            manager.save()
        self.stdout.write(f"{'Created' if created else 'Exists'}: manager@mail.com (org admin)")

        # 设置 org.admin_user
        if org.admin_user != manager:
            org.admin_user = manager
            org.save()

        # IEEE 组织编辑
        editor, created = User.objects.get_or_create(
            email='editor@mail.com',
            defaults={
                'username': 'editor',
                'role': 'publisher',
                'organization': org,
                'permission': 1110,
            }
        )
        if created or not editor.check_password(PASSWORD):
            editor.set_password(PASSWORD)
            editor.save()
        self.stdout.write(f"{'Created' if created else 'Exists'}: editor@mail.com (publisher)")

        # IEEE 组织专家
        expert, created = User.objects.get_or_create(
            email='expert@mail.com',
            defaults={
                'username': 'expert',
                'role': 'reviewer',
                'organization': org,
                'permission': 1,
            }
        )
        if created or not expert.check_password(PASSWORD):
            expert.set_password(PASSWORD)
            expert.save()
        self.stdout.write(f"{'Created' if created else 'Exists'}: expert@mail.com (reviewer)")

        self.stdout.write(self.style.SUCCESS('Done. All passwords: 123456'))
