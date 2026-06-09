"""
Task 6: Bridge tier — paper detection mocks HTTP at requests.post level.

This tests the full call stack including detect_text_segment → requests.post
without any real network calls. Uses unittest.mock to intercept at the
HTTP boundary, simulating what the FastDetect API returns.
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
    "Abstract\n\nThis paper presents a novel approach to AI text detection.\n\n"
    "Introduction\n\nAI-generated text is difficult to distinguish from human writing.\n\n"
    "Method\n\nWe use a transformer-based approach with a fine-tuned classifier.\n\n"
    "Conclusion\n\nResults show 95% accuracy on benchmark datasets.\n"
)


def _fastdetect_http_response(prob: float = 0.88) -> MagicMock:
    """Build a mock requests.Response that mimics FastDetect API output."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "data": {
            "prob": prob,
            "details": {
                "label": "AI" if prob >= 0.5 else "Human",
                "confidence": prob,
            }
        }
    }
    return mock_resp


def _write_paper(media_root: str, rel="papers/bridge_test.txt") -> str:
    full = os.path.join(media_root, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(_PAPER_TEXT)
    return rel


@patch.dict(os.environ, {"FASTDETECT_API_KEY": "test-key-000"})
@patch(
    "core.views.views_dectection.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
@patch(
    "core.services.capabilities.llm.fastdetect_client.requests.post",
    side_effect=lambda *a, **kw: _fastdetect_http_response(prob=0.88),
)
@patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda f: f())
def test_paper_bridge_tier_fastdetect_http_mock(mock_on_commit, mock_post, mock_starter, tmp_path):
    """
    Bridge tier: mock requests.post inside fastdetect_client.
    Verify the full chain processes the HTTP response correctly:
    - task completes
    - paragraph_results contain probability derived from mocked HTTP response
    - detect_text_segment was NOT called with real network
    """
    tmp_media = str(tmp_path)
    with override_settings(MEDIA_ROOT=tmp_media):
        user = make_user(role="publisher")
        stored = _write_paper(tmp_media)
        paper_file = make_file_management(
            user=user, resource_type="paper",
            stored_path=stored, file_name="bridge_test.txt",
        )

        client = APIClient()
        client.force_authenticate(user)

        resp = client.post(CREATE_URL, {
            "task_type": "paper",
            "file_ids": [paper_file.id],
            "task_name": "Bridge tier paper test",
        }, format="json")

        assert resp.status_code in (200, 201), f"Create failed: {resp.data}"
        task_id = resp.data["task_id"]

        task = DetectionTask.objects.get(id=task_id)
        assert task.status == "completed", (
            f"Expected completed, got {task.status!r}: {task.error_message!r}"
        )

        # Verify requests.post was actually called (not short-circuited)
        assert mock_post.called, (
            "requests.post was never called — fastdetect_client did not make HTTP request"
        )

        # Verify call arguments include detector and text fields
        call_kwargs = mock_post.call_args
        payload_sent = call_kwargs.kwargs.get("json") or (
            call_kwargs.args[1] if len(call_kwargs.args) > 1 else {}
        )
        assert "text" in payload_sent, (
            f"FastDetect HTTP payload missing 'text' field: {payload_sent}"
        )
        assert "detector" in payload_sent, (
            f"FastDetect HTTP payload missing 'detector' field: {payload_sent}"
        )

        # Verify results reflect the mocked 0.88 probability
        results_resp = client.get(RESULTS_URL.format(task_id))
        assert results_resp.status_code == 200
        items = (results_resp.data.get("results") or {})
        para_results = items.get("paragraph_results") or []
        high_prob = [p for p in para_results if p.get("probability", 0) >= 0.5]
        assert high_prob, (
            f"No paragraph with probability >= 0.5 despite HTTP mock returning 0.88. "
            f"paragraph_results={para_results}"
        )


@patch.dict(os.environ, {"FASTDETECT_API_KEY": "test-key-000"})
@patch(
    "core.views.views_dectection.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
@patch(
    "core.services.capabilities.llm.fastdetect_client.requests.post",
    side_effect=lambda *a, **kw: _fastdetect_http_response(prob=0.12),
)
@patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda f: f())
def test_paper_bridge_tier_low_probability_classified_clean(mock_on_commit, mock_post, mock_starter, tmp_path):
    """
    When FastDetect returns a low probability (0.12), paragraphs should have
    label='clean' (threshold is 0.5).
    """
    tmp_media = str(tmp_path)
    with override_settings(MEDIA_ROOT=tmp_media):
        user = make_user(role="publisher")
        stored = _write_paper(tmp_media, "papers/low_prob.txt")
        paper_file = make_file_management(
            user=user, resource_type="paper",
            stored_path=stored, file_name="low_prob.txt",
        )

        client = APIClient()
        client.force_authenticate(user)

        resp = client.post(CREATE_URL, {
            "task_type": "paper",
            "file_ids": [paper_file.id],
            "task_name": "Low prob test",
        }, format="json")

        assert resp.status_code in (200, 201)
        task = DetectionTask.objects.get(id=resp.data["task_id"])
        assert task.status == "completed"

        results_resp = client.get(RESULTS_URL.format(task.id))
        para_results = (results_resp.data.get("results") or {}).get("paragraph_results") or []
        clean_paras = [p for p in para_results if p.get("label") == "clean"]
        suspicious_paras = [p for p in para_results if p.get("label") == "suspicious"]
        assert len(clean_paras) > 0 or len(para_results) == 0, (
            "Expected clean paragraphs with prob=0.12 but got none"
        )
        assert len(suspicious_paras) == 0, (
            f"No paragraphs should be suspicious at prob=0.12, found: {suspicious_paras}"
        )
