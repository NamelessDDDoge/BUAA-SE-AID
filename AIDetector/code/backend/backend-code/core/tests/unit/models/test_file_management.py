"""5.6 FileManagement 表"""
import pytest

from core.models import FileManagement
from core.tests.factories import make_file_management, make_user

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_str_contains_file_name_and_username():
    user = make_user(username="bob")
    f = make_file_management(user=user, file_name="paper.pdf")
    rendered = str(f)
    assert "paper.pdf" in rendered
    assert "bob" in rendered


def test_default_resource_type_is_image():
    f = make_file_management()
    assert f.resource_type == "image"


def test_default_tag_is_other():
    f = make_file_management()
    assert f.tag == "Other"


def test_default_stored_path_is_empty_string():
    f = make_file_management()
    assert f.stored_path == ""


def test_resource_type_accepts_all_four_choices():
    user = make_user()
    for rt in ("image", "paper", "review_paper", "review_file"):
        f = FileManagement.objects.create(
            user=user,
            organization=user.organization,
            file_name="x.bin",
            file_size=10,
            file_type="x",
            resource_type=rt,
        )
        assert f.resource_type == rt


def test_linked_file_can_chain_self_reference():
    parent = make_file_management(resource_type="paper")
    child = make_file_management(user=parent.user, resource_type="image", linked_file=parent)
    assert child.linked_file_id == parent.id
    assert parent.linked_children.filter(id=child.id).exists()


def test_upload_time_defaulted_on_create():
    f = make_file_management()
    assert f.upload_time is not None
