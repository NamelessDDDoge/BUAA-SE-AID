"""LLMModel — DTC-ADMIN-10 模型状态管理

代码里实际存在但《概要设计》5.x 表列表未列出的模型。
"""
import pytest
from django.db import IntegrityError

from core.models import LLMModel
from core.tests.factories import make_llm_model

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_model_name_must_be_unique():
    make_llm_model(model_name="deepseek-chat")
    with pytest.raises(IntegrityError):
        LLMModel.objects.create(
            model_name="deepseek-chat",
            display_name="DeepSeek Other",
            provider="openai_compat",
            model_type="chat",
        )


def test_default_provider_and_type_and_is_active():
    m = LLMModel.objects.create(
        model_name="llm-default-test", display_name="Test",
    )
    assert m.provider == "openai_compat"
    assert m.model_type == "chat"
    assert m.is_active is True


def test_model_type_accepts_chat_and_fastdetect():
    for mt in ("chat", "fastdetect"):
        m = make_llm_model(model_type=mt)
        assert m.model_type == mt


def test_str_includes_display_and_model_name():
    m = make_llm_model(model_name="x-y-z", display_name="X Y Z")
    rendered = str(m)
    assert "X Y Z" in rendered
    assert "x-y-z" in rendered


def test_created_and_updated_at_set_automatically():
    m = make_llm_model()
    assert m.created_at is not None
    assert m.updated_at is not None


def test_can_deactivate_model():
    m = make_llm_model()
    m.is_active = False
    m.save()
    m.refresh_from_db()
    assert m.is_active is False
