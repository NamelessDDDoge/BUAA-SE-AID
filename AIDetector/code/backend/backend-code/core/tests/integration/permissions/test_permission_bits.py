"""难点 2.2.3 — 4 位二进制权限编码（上传/提交/发布/审核）"""
import pytest

from core.tests.factories import make_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


# 权限位说明（来自 models.User.has_permission）：
# permission = "abcd" 4 位字符串，位置：[0]=upload, [1]=submit, [2]=publish, [3]=review
# - publisher 默认 1110: upload + submit + publish，不能 review
# - reviewer  默认 0001: 仅 review
# - admin     无组织，permission=None


def test_publisher_can_upload_submit_publish():
    u = make_user(role="publisher")
    for p in ("upload", "submit", "publish"):
        assert u.has_permission(p) is True


def test_publisher_cannot_review():
    u = make_user(role="publisher")
    assert u.has_permission("review") is False


def test_reviewer_can_only_review():
    u = make_user(role="reviewer")
    assert u.has_permission("review") is True
    for p in ("upload", "submit", "publish"):
        assert u.has_permission(p) is False


def test_admin_role_has_no_permissions():
    u = make_user(role="admin")
    for p in ("upload", "submit", "publish", "review"):
        assert u.has_permission(p) is False


def test_unknown_perm_type_returns_false():
    u = make_user(role="publisher")
    assert u.has_permission("delete_anything") is False
    assert u.has_permission("") is False


def test_user_without_organization_loses_all_permissions():
    u = make_user(role="publisher")
    u.organization = None
    u.save_permission()
    assert u.has_permission("upload") is False


def test_manual_permission_override_persists():
    # 设置自定义权限位（只有 publish + review）
    u = make_user(role="publisher")
    u.permission = 11  # "0011" → publish=False, review... 等等
    u.save_permission()  # 不走 save() 重置逻辑
    u.refresh_from_db()
    perm_str = str(u.permission).zfill(4)
    # 验证 4 位字符串语义
    assert perm_str == "0011"
    assert u.has_permission("upload") is False
    assert u.has_permission("submit") is False
    assert u.has_permission("publish") is True
    assert u.has_permission("review") is True


def test_save_resets_permission_based_on_role():
    # 即使手动设置过 permission，save() 会按 role 重置
    u = make_user(role="publisher")
    u.permission = 0
    u.save()
    u.refresh_from_db()
    assert u.permission == 1110
