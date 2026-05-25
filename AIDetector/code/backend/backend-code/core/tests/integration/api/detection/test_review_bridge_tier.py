"""
Task 7: Bridge tier — review detection mocks HTTP at requests.post level
inside openai_client (OpenAI-compatible chat completions endpoint).

The openai_client._request_structured_json function calls requests.post
to an OpenAI-compatible endpoint. We mock that HTTP call to return a
structured JSON blob (the kind that analyze_review_text expects).
"""
import os
import json
import pytest
from unittest.mock import patch, MagicMock
from django.test import override_settings
from rest_framework.test import APIClient

from core.models import DetectionTask
from core.services.orchestrators.resource_task_orchestrator import run_resource_detection_task_async
from core.tests.factories import make_user, make_file_management

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

CREATE_URL = "/api/resource-task/create/"
RESULTS_URL = "/api/paper-results/{}/"

_PAPER_TEXT = (
    "Abstract\n\nThis paper studies the impact of AI on peer review quality.\n\n"
    "Introduction\n\nPeer review is fundamental to scientific publishing.\n\n"
    "Conclusion\n\nAI-generated reviews are increasingly common.\n"
)

_REVIEW_TEXT = (
    "Summary\n\nThe paper makes a strong contribution to the field.\n\n"
    "Strengths\n\nThe literature review is comprehensive.\n\n"
    "Weaknesses\n\nThe sample size is small.\n"
)

_STRUCTURED_REVIEW_RESPONSE = {
    "overall": {
        "template_like_level": "low",
        "wrongness_level": "low",
        "relevance_level": "high",
        "summary": "Review is genuine and thorough.",
        "key_findings": ["Comprehensive literature review"],
        "suggestions": ["Expand sample size"],
    },
    "paragraph_results": [
        {
            "review_paragraph_index": 0,
            "paper_paragraph_index": 0,
            "template_like_level": "low",
            "wrongness_level": "low",
            "relevance_score": 0.90,
            "relevance_level": "high",
            "explanation": "Reviewer directly references the paper's abstract.",
        },
        {
            "review_paragraph_index": 1,
            "paper_paragraph_index": None,
            "template_like_level": "medium",
            "wrongness_level": "low",
            "relevance_score": 0.50,
            "relevance_level": "medium",
            "explanation": "Generic strength comment.",
        },
    ],
}


def _openai_chat_completion_response(content: dict) -> MagicMock:
    """
    Simulate an OpenAI-compatible chat completions HTTP response.
    The content dict will be JSON-encoded into choices[0].message.content.
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(content),
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
    }
    return mock_resp


def _write_file(media_root: str, rel: str, text: str) -> str:
    full = os.path.join(media_root, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(text)
    return rel


@patch(
    "core.views.views_dectection.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
@patch(
    "core.services.capabilities.llm.openai_client.requests.post",
    side_effect=lambda *a, **kw: _openai_chat_completion_response(_STRUCTURED_REVIEW_RESPONSE),
)
@patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda f: f())
@patch(
    "core.services.capabilities.llm.openai_client.get_llm_runtime_config",
    return_value={"endpoint": "http://fake-llm/v1/chat/completions", "model": "gpt-4", "key": "fake-key"},
)
def test_review_bridge_tier_openai_http_mock(mock_llm_config, mock_on_commit, mock_post, mock_starter, tmp_path):
    """
    Bridge tier: mock requests.post inside openai_client.
    Verify the full chain processes the HTTP response correctly:
    - task completes
    - paragraph_results reflect the mocked API response
    - overall review_analysis_results present
    """
    tmp_media = str(tmp_path)
    with override_settings(MEDIA_ROOT=tmp_media):
        user = make_user(role="publisher")

        paper_stored = _write_file(tmp_media, "review_bridge/paper.txt", _PAPER_TEXT)
        review_stored = _write_file(tmp_media, "review_bridge/review.txt", _REVIEW_TEXT)

        paper_file = make_file_management(
            user=user, resource_type="review_paper",
            stored_path=paper_stored, file_name="paper.txt",
        )
        review_file = make_file_management(
            user=user, resource_type="review_file",
            stored_path=review_stored, file_name="review.txt",
            linked_file=paper_file,
        )

        client = APIClient()
        client.force_authenticate(user)

        resp = client.post(CREATE_URL, {
            "task_type": "review",
            "file_ids": [paper_file.id, review_file.id],
            "task_name": "Bridge tier review test",
        }, format="json")

        assert resp.status_code in (200, 201), f"Create failed: {resp.data}"
        task_id = resp.data["task_id"]

        task = DetectionTask.objects.get(id=task_id)
        assert task.status == "completed", (
            f"Expected completed, got {task.status!r}: {task.error_message!r}"
        )

        # Verify requests.post was called (chain reached the HTTP layer)
        assert mock_post.called, (
            "requests.post was never called — openai_client did not make HTTP request"
        )

        results_resp = client.get(RESULTS_URL.format(task_id))
        assert results_resp.status_code == 200
        data = results_resp.data
        assert data["status"] == "completed"

        results = data.get("results") or {}
        para_results = results.get("paragraph_results") or []
        assert len(para_results) > 0, "paragraph_results must not be empty"

        review_analysis = results.get("review_analysis_results")
        assert review_analysis is not None
        overall = review_analysis.get("overall") or {}
        assert "template_like_level" in overall
        assert "qualification_label" in overall, (
            "'qualification_label' missing from overall — build_review_qualification not applied"
        )


@patch(
    "core.views.views_dectection.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
@patch(
    "core.services.capabilities.llm.openai_client.requests.post",
    side_effect=ConnectionError("OpenAI endpoint unreachable"),
)
@patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda f: f())
@patch(
    "core.services.capabilities.llm.openai_client.get_llm_runtime_config",
    return_value={"endpoint": "http://fake-llm/v1/chat/completions", "model": "gpt-4", "key": "fake-key"},
)
def test_review_bridge_tier_api_error_results_in_unavailable(mock_llm_config, mock_on_commit, mock_post, mock_starter, tmp_path):
    """
    When the OpenAI-compatible endpoint is unreachable, evaluate_review_analysis
    returns an 'api_unavailable' overall. The task should still complete
    (not fail) and overall.qualification_label should be 'unavailable'.
    """
    tmp_media = str(tmp_path)
    with override_settings(MEDIA_ROOT=tmp_media):
        user = make_user(role="publisher")

        paper_stored = _write_file(tmp_media, "review_bridge/paper_err.txt", _PAPER_TEXT)
        review_stored = _write_file(tmp_media, "review_bridge/review_err.txt", _REVIEW_TEXT)

        paper_file = make_file_management(
            user=user, resource_type="review_paper",
            stored_path=paper_stored, file_name="paper_err.txt",
        )
        review_file = make_file_management(
            user=user, resource_type="review_file",
            stored_path=review_stored, file_name="review_err.txt",
            linked_file=paper_file,
        )

        client = APIClient()
        client.force_authenticate(user)

        resp = client.post(CREATE_URL, {
            "task_type": "review",
            "file_ids": [paper_file.id, review_file.id],
            "task_name": "API error review test",
        }, format="json")

        assert resp.status_code in (200, 201), f"Create failed: {resp.data}"
        task = DetectionTask.objects.get(id=resp.data["task_id"])

        # evaluate_review_analysis handles the error gracefully; task must not crash
        assert task.status == "completed", (
            f"Task should complete even when OpenAI endpoint is down, got {task.status!r}: "
            f"{task.error_message!r}"
        )

        results_resp = client.get(RESULTS_URL.format(task.id))
        assert results_resp.status_code == 200
        results = results_resp.data.get("results") or {}
        review_analysis = results.get("review_analysis_results") or {}
        overall = review_analysis.get("overall") or {}

        # When LLM is unavailable, overall should reflect that
        qualification = overall.get("qualification_label", "")
        assert qualification == "unavailable", (
            f"Expected qualification_label='unavailable' when API unreachable, got {qualification!r}"
        )
