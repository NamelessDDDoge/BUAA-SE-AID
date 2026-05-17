"""factory_boy 工厂入口。

骨架阶段空实现。后续 PR 在此为 18 张数据表分别建工厂，例如::

    import factory
    from core.models import Organization, User

    class OrganizationFactory(factory.django.DjangoModelFactory):
        class Meta:
            model = Organization
        name = factory.Sequence(lambda n: f"org-{n}")
        # ...
"""
