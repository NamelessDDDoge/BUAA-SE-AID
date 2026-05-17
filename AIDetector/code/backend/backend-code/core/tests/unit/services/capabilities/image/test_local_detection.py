"""capabilities/image/local_detection — 纯函数 / 解析逻辑单测

集成测试（subprocess + DB）见 core/tests/integration/api/detection/test_image_detection_flow.py。
这里只覆盖 _payload_by_name / _extract_*  / _normalize_task_parameters 的边界。
"""
import numpy as np
import pytest

from core.services.capabilities.image import local_detection as ld

pytestmark = pytest.mark.unit


# ---------- _payload_by_name ----------

def test_payload_by_name_indexes_by_first_element():
    raw = [("llm", [1, 2]), ("ela", [3])]
    out = ld._payload_by_name(raw)
    assert out == {"llm": [1, 2], "ela": [3]}


def test_payload_by_name_skips_malformed_entries():
    raw = [("ok", [1]), ("too-few",), "not-a-tuple", ("nest", [2])]
    out = ld._payload_by_name(raw)
    assert "ok" in out and "nest" in out
    assert "too-few" not in out


def test_payload_by_name_returns_empty_for_none():
    assert ld._payload_by_name(None) == {}


# ---------- _extract_second_item ----------

def test_extract_second_item_returns_second_when_pair():
    assert ld._extract_second_item([("name", 42)], 0) == 42


def test_extract_second_item_returns_entry_when_not_a_pair():
    assert ld._extract_second_item([99], 0) == 99


def test_extract_second_item_returns_none_when_index_out_of_range():
    assert ld._extract_second_item([], 0) is None
    assert ld._extract_second_item([1], 5) is None


# ---------- _extract_exif_entry ----------

def test_extract_exif_entry_unwraps_nested_tuple():
    entry = [("a.png", ("exif", ["Edited by Photoshop"]))]
    assert ld._extract_exif_entry(entry, 0) == ["Edited by Photoshop"]


def test_extract_exif_entry_returns_second_when_payload_not_nested():
    entry = [("a.png", "raw-payload")]
    assert ld._extract_exif_entry(entry, 0) == "raw-payload"


def test_extract_exif_entry_none_when_index_invalid():
    assert ld._extract_exif_entry([], 0) is None


# ---------- _extract_method_entry ----------

def test_extract_method_entry_pair_form():
    mask = np.zeros((4, 4))
    entries = [(mask, 0.42)]
    out_mask, prob = ld._extract_method_entry(entries, 0)
    assert prob == pytest.approx(0.42)
    assert np.array_equal(out_mask, mask)


def test_extract_method_entry_flat_pair_stride():
    entries = ["m0", 0.1, "m1", 0.9]
    out_mask, prob = ld._extract_method_entry(entries, 1)
    assert out_mask == "m1"
    assert prob == 0.9


def test_extract_method_entry_nested_wrapper():
    entries = [["m0", 0.1, "m1", 0.7]]
    out_mask, prob = ld._extract_method_entry(entries, 1)
    assert out_mask == "m1"
    assert prob == 0.7


def test_extract_method_entry_default_when_none():
    mask, prob = ld._extract_method_entry(None, 0)
    assert prob == 0.0
    assert mask.shape == (8, 8)


def test_extract_method_entry_default_when_index_out_of_range():
    mask, prob = ld._extract_method_entry([], 5)
    assert prob == 0.0
    assert mask.shape == (8, 8)


# ---------- _parse_llm_entry ----------

def test_parse_llm_entry_extracts_outputs_from_dict():
    text, mask = ld._parse_llm_entry(("img.png", {"outputs": "AI-generated", "mask": "m"}))
    assert text == "AI-generated"
    assert mask == "m"


def test_parse_llm_entry_handles_payload_that_is_list_with_dict_head():
    # 形式：("img.png", [{"outputs": "x"}, "mask-bytes"])
    text, mask = ld._parse_llm_entry(("img.png", [{"outputs": "x"}, "mask-bytes"]))
    assert text == "x"
    assert mask == "mask-bytes"


def test_parse_llm_entry_handles_payload_that_is_list_with_string_head():
    # 形式：("img.png", ["text-only", "mask"])
    text, mask = ld._parse_llm_entry(("img.png", ["text-only", "mask"]))
    assert text == "text-only"
    assert mask == "mask"


def test_parse_llm_entry_returns_empty_when_payload_none():
    text, mask = ld._parse_llm_entry(("img.png", None))
    assert text == ""
    assert mask is None


def test_parse_llm_entry_stringifies_unknown_payload():
    text, mask = ld._parse_llm_entry(("img.png", 42))
    assert text == "42"
    assert mask is None


# ---------- _normalize_task_parameters ----------

class _FakeTask:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def test_normalize_task_parameters_defaults_when_block_size_invalid():
    out = ld._normalize_task_parameters(_FakeTask(
        cmd_block_size=None, urn_k=None, if_use_llm=False,
        llm_model_name=None, method_switches=None,
    ))
    assert out["cmd_block_size"] == 64
    assert out["urn_k"] == 0.3
    assert out["if_use_llm"] is False
    assert out["llm_model_name"] is None


def test_normalize_task_parameters_keeps_valid_values():
    out = ld._normalize_task_parameters(_FakeTask(
        cmd_block_size=128, urn_k=0.45, if_use_llm=True,
        llm_model_name="deepseek-chat",
        method_switches={"ela": True},
    ))
    assert out["cmd_block_size"] == 128
    assert out["urn_k"] == pytest.approx(0.45)
    assert out["if_use_llm"] is True
    assert out["llm_model_name"] == "deepseek-chat"
    assert out["method_switches"] == {"ela": True}


def test_normalize_task_parameters_block_size_below_2_falls_back_to_64():
    out = ld._normalize_task_parameters(_FakeTask(
        cmd_block_size=1, urn_k=0.2, if_use_llm=False,
        llm_model_name=None, method_switches=None,
    ))
    assert out["cmd_block_size"] == 64


# ---------- _extract_single_result ----------

def test_extract_single_result_assembles_full_structure():
    raw = [
        ("llm", [("a.png", {"outputs": "AI"})]),
        ("ela", [("a.png", np.array([[1, 2]], dtype=np.uint8))]),
        ("exif", [("a.png", ("exif", ["Edited by Photoshop"]))]),
        ("urn_coarse_v2", [(np.zeros((2, 2)), 0.8)]),
        ("urn_blurring", []),
        ("urn_brute_force", []),
        ("urn_contrast", []),
        ("urn_inpainting", []),
    ]
    out = ld._extract_single_result(raw, 0)
    assert out["llm_text"] == "AI"
    assert out["overall_is_fake"] is True
    assert out["exif_flags"]["photoshop"] is True
    assert out["overall_confidence"] == 1.0
    assert any(s["method"] == "splicing" and s["prob"] == 0.8 for s in out["sub_method_results"])


def test_extract_single_result_no_exif_no_high_prob_means_real():
    raw = [
        ("llm", []),
        ("ela", []),
        ("exif", []),
        ("urn_coarse_v2", [(np.zeros((2, 2)), 0.1)]),
        ("urn_blurring", []),
        ("urn_brute_force", []),
        ("urn_contrast", []),
        ("urn_inpainting", []),
    ]
    out = ld._extract_single_result(raw, 0)
    assert out["overall_is_fake"] is False
    assert out["exif_flags"] == {"photoshop": False, "time_modified": False}
