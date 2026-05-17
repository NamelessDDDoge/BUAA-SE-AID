"""capabilities/review_relevance_service — 纯函数，无外部依赖"""
import pytest

from core.services.capabilities.review_relevance_service import (
    _build_explanation,
    _overlap_score,
    _tokenize,
    analyze_review_relevance,
)

pytestmark = pytest.mark.unit


def test_tokenize_splits_alphanumeric_and_chinese():
    tokens = _tokenize("Image forgery 图像 篡改 ab")
    assert "image" in tokens
    assert "forgery" in tokens
    assert "图像" in tokens
    assert "篡改" in tokens
    assert "ab" in tokens


def test_tokenize_drops_single_char_tokens():
    tokens = _tokenize("a bc d ef")
    assert "a" not in tokens
    assert "d" not in tokens
    assert "bc" in tokens
    assert "ef" in tokens


def test_tokenize_returns_empty_set_for_empty_text():
    assert _tokenize("") == set()
    assert _tokenize(None) == set()


def test_tokenize_lowercases_alphabetic_tokens():
    tokens = _tokenize("Apple BANANA cherry")
    assert "apple" in tokens
    assert "banana" in tokens
    assert "cherry" in tokens


def test_overlap_score_returns_zero_for_empty_review_tokens():
    assert _overlap_score(set(), {"any"}) == 0.0


def test_overlap_score_is_ratio_of_overlap_to_review_tokens():
    review = {"a", "b", "c", "d"}
    overlap = {"a", "b"}
    assert _overlap_score(review, overlap) == pytest.approx(0.5)


def test_overlap_score_rounded_to_4_decimals():
    # 1/3 ≈ 0.3333
    review = {"a", "b", "c"}
    overlap = {"a"}
    assert _overlap_score(review, overlap) == 0.3333


def test_build_explanation_when_no_best_match():
    assert _build_explanation(None, set(), 0.0).startswith("No matching")


def test_build_explanation_when_no_overlap_tokens():
    best_match = {"paragraph_index": 2, "text": "x"}
    msg = _build_explanation(best_match, set(), 0.0)
    assert "little lexical overlap" in msg


def test_build_explanation_when_overlap_exists():
    best_match = {"paragraph_index": 3, "text": "x"}
    msg = _build_explanation(best_match, {"a", "b"}, 0.6)
    assert "#3" in msg
    assert "2 shared terms" in msg
    assert "0.60" in msg


def test_analyze_review_relevance_picks_best_paper_paragraph_by_overlap():
    paper = [
        "The method uses convolution neural network for image forgery detection",
        "Bananas are tasty fruit not used in academic papers",
    ]
    review = [
        "The CNN convolution module helps to detect image forgery",
    ]
    out = analyze_review_relevance(review_segments=review, paper_segments=paper)
    assert len(out) == 1
    assert out[0]["paper_paragraph_index"] == 0
    assert out[0]["label"] in {"relevant", "weak_match"}
    assert out[0]["review_paragraph_index"] == 0
    assert out[0]["review_text"].startswith("The CNN")


def test_analyze_review_relevance_label_relevant_when_score_above_threshold():
    paper = ["alpha beta gamma delta epsilon"]
    review = ["alpha beta gamma"]  # 3/3 = 1.0 overlap
    out = analyze_review_relevance(review_segments=review, paper_segments=paper)
    assert out[0]["label"] == "relevant"
    assert out[0]["relevance_score"] >= 0.2


def test_analyze_review_relevance_label_weak_match_when_score_below_threshold():
    paper = ["alpha beta gamma"]
    review = ["zeta eta theta iota kappa lambda alpha"]  # overlap=1, review tokens=7
    out = analyze_review_relevance(review_segments=review, paper_segments=paper)
    # 1/7 ≈ 0.14 < 0.2
    assert out[0]["label"] == "weak_match"


def test_analyze_review_relevance_empty_paper_returns_null_best_match():
    out = analyze_review_relevance(review_segments=["hello world"], paper_segments=[])
    assert out[0]["paper_paragraph_index"] is None
    assert out[0]["paper_text"] == ""
    assert out[0]["relevance_score"] == 0.0
