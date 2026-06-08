import shutil
from pathlib import Path
from unittest.mock import patch

from reportlab.pdfgen import canvas
from django.test import TestCase, override_settings

from core.models import (
    DetectionTask,
    FileManagement,
    Organization,
    PaperDetectionResult,
    ReviewDetectionResult,
    User,
    LLMModel,
)
from core.services.capabilities.llm.runtime_config import get_fastdetect_runtime_config
from core.services.resources.document_preprocessor import (
    extract_document_paragraphs,
    extract_pdf_tables,
    preprocess_document,
)
from core.services.resources.text_sanitizer import sanitize_json_like
from core.services.capabilities.llm_analysis_service import build_overall_paper_evaluation
from core.tasks import run_paper_detection, run_review_detection


@override_settings(ENABLE_FANYI=False)
class ResourcePreprocessingTests(TestCase):
    def setUp(self):
        temp_root = Path.home() / ".codex" / "memories" / "buaa-se-aid-resource-preprocess-tests"
        shutil.rmtree(temp_root, ignore_errors=True)
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_media = temp_root
        self.override = override_settings(MEDIA_ROOT=str(temp_root))
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(lambda: shutil.rmtree(self.temp_media, ignore_errors=True))

        self.organization = Organization.objects.create(name="Preprocess Org", email="preprocess-org@example.com")
        self.user = User.objects.create_user(
            username="preprocess-user",
            email="preprocess-user@example.com",
            password="pass123456",
            role="publisher",
            organization=self.organization,
        )

    def create_text_file(self, file_name, content):
        uploads_dir = self.temp_media / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        file_path = uploads_dir / file_name
        file_path.write_text(content, encoding="utf-8")
        return FileManagement.objects.create(
            user=self.user,
            organization=self.organization,
            file_name=file_name,
            file_size=file_path.stat().st_size,
            file_type="text/plain",
            resource_type="paper",
            stored_path=f"uploads/{file_name}",
        )

    def create_review_file(self, file_name, content, *, resource_type, linked_file=None):
        uploads_dir = self.temp_media / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        file_path = uploads_dir / file_name
        file_path.write_text(content, encoding="utf-8")
        return FileManagement.objects.create(
            user=self.user,
            organization=self.organization,
            file_name=file_name,
            file_size=file_path.stat().st_size,
            file_type="text/plain",
            resource_type=resource_type,
            stored_path=f"uploads/{file_name}",
            linked_file=linked_file,
        )

    def create_pdf_file(self, file_name, text, *, resource_type="paper"):
        uploads_dir = self.temp_media / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        file_path = uploads_dir / file_name
        pdf = canvas.Canvas(str(file_path))
        pdf.drawString(72, 760, text)
        pdf.save()
        return FileManagement.objects.create(
            user=self.user,
            organization=self.organization,
            file_name=file_name,
            file_size=file_path.stat().st_size,
            file_type="application/pdf",
            resource_type=resource_type,
            stored_path=f"uploads/{file_name}",
        )

    def create_table_like_pdf_file(self, file_name):
        uploads_dir = self.temp_media / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        file_path = uploads_dir / file_name
        pdf = canvas.Canvas(str(file_path))
        pdf.drawString(72, 760, "This paragraph should remain normal text for AIGC analysis.")
        rows = [
            ("Method", "Accuracy", "F1"),
            ("Baseline", "81.2", "79.5"),
            ("Ours", "91.4", "90.1"),
        ]
        y = 710
        for row in rows:
            pdf.drawString(72, y, row[0])
            pdf.drawString(220, y, row[1])
            pdf.drawString(330, y, row[2])
            y -= 18
        pdf.save()
        return FileManagement.objects.create(
            user=self.user,
            organization=self.organization,
            file_name=file_name,
            file_size=file_path.stat().st_size,
            file_type="application/pdf",
            resource_type="paper",
            stored_path=f"uploads/{file_name}",
        )

    @patch("core.services.orchestrators.paper_task_orchestrator.run_image_detection_task")
    @patch("core.services.capabilities.llm.fastdetect_client.requests.post")
    def test_run_paper_detection_splits_text_into_500_char_segments(self, mock_post, mock_image_detection):
        mock_post.return_value.json.return_value = {"data": {"prob": 0.65, "details": {"source": "mock"}}}
        mock_post.return_value.raise_for_status.return_value = None
        file_record = self.create_text_file(
            "paper.txt",
            "A" * 3300,
        )
        task = DetectionTask.objects.create(
            user=self.user,
            organization=self.organization,
            task_type="paper",
            task_name="Segmented Paper",
            status="pending",
        )
        task.resource_files.add(file_record)

        result = run_paper_detection(task.id)

        task.refresh_from_db()
        self.assertEqual(result, "Paper detection finished")
        self.assertEqual(task.status, "completed")
        self.assertEqual(task.text_detection_results["document"]["segment_count"], 3)
        self.assertEqual(len(task.text_detection_results["paragraph_results"]), 3)
        self.assertEqual(len(task.text_detection_results["suspicious_paragraphs"]), 3)
        self.assertEqual(task.completion_time is not None, True)
        self.assertEqual(mock_post.call_count, 3)
        self.assertTrue(all(item["text"] for item in task.text_detection_results["paragraph_results"]))
        self.assertTrue(PaperDetectionResult.objects.filter(detection_task=task).exists())
        self.assertEqual(task.paper_detection_result.paragraph_results.count(), 3)
        mock_image_detection.assert_not_called()

    @patch("core.services.orchestrators.paper_task_orchestrator.run_image_detection_task")
    @patch("core.services.capabilities.llm.fastdetect_client.requests.post")
    def test_run_paper_detection_skips_image_detection_when_extract_images_disabled(self, mock_post, mock_image_detection):
        mock_post.return_value.json.return_value = {"data": {"prob": 0.42, "details": {"source": "mock"}}}
        mock_post.return_value.raise_for_status.return_value = None
        file_record = self.create_text_file("paper.pdf", "Paragraph one.\nParagraph two.")
        task = DetectionTask.objects.create(
            user=self.user,
            organization=self.organization,
            task_type="paper",
            task_name="Paper Without Images",
            status="pending",
            method_switches={
                "__paper_extract_images__": False,
                "llm": False,
                "ela": False,
                "exif": False,
                "cmd": False,
                "urn_coarse_v2": False,
                "urn_blurring": False,
                "urn_brute_force": False,
                "urn_contrast": False,
                "urn_inpainting": False,
            },
        )
        task.resource_files.add(file_record)

        run_paper_detection(task.id)

        task.refresh_from_db()
        self.assertEqual(task.status, "completed")
        self.assertEqual(task.text_detection_results["image_results"], [])
        self.assertEqual(task.text_detection_results["document"]["image_detection_enabled"], False)
        self.assertFalse(task.paper_detection_result.image_detection_enabled)
        mock_image_detection.assert_not_called()

    @patch("core.services.orchestrators.paper_task_orchestrator.run_image_detection_task")
    @patch("core.services.capabilities.llm.fastdetect_client.requests.post")
    def test_run_paper_detection_aggregates_multiple_paper_files_into_items(self, mock_post, mock_image_detection):
        mock_post.return_value.json.return_value = {"data": {"prob": 0.2, "details": {"source": "mock"}}}
        mock_post.return_value.raise_for_status.return_value = None
        file_record_1 = self.create_text_file("paper-a.txt", "Paper A paragraph.")
        file_record_2 = self.create_text_file("paper-b.txt", "Paper B paragraph.")
        task = DetectionTask.objects.create(
            user=self.user,
            organization=self.organization,
            task_type="paper",
            task_name="Multi Paper Detection",
            status="pending",
        )
        task.resource_files.add(file_record_1, file_record_2)

        result = run_paper_detection(task.id)

        task.refresh_from_db()
        self.assertEqual(result, "Paper detection finished")
        self.assertEqual(task.status, "completed")
        self.assertEqual(task.text_detection_results["document"]["resource_count"], 2)
        self.assertEqual(len(task.text_detection_results["items"]), 2)
        self.assertEqual(task.text_detection_results["items"][0]["document"]["file_name"], "paper-a.txt")
        self.assertEqual(task.text_detection_results["items"][1]["document"]["file_name"], "paper-b.txt")
        self.assertEqual(task.text_detection_results["document"]["file_name"], "paper-a.txt")
        mock_image_detection.assert_not_called()

    @patch("core.services.orchestrators.paper_task_orchestrator.run_image_detection_task")
    @patch("core.services.capabilities.llm.fastdetect_client.requests.post")
    def test_run_paper_detection_stops_on_fastdetect_402_billing_error(self, mock_post, mock_image_detection):
        mock_post.side_effect = RuntimeError("server 402 payment required")
        file_record = self.create_text_file(
            "paper-billing.txt",
            "First paragraph should trigger billing failure.\n\nSecond paragraph should not be called.",
        )
        task = DetectionTask.objects.create(
            user=self.user,
            organization=self.organization,
            task_type="paper",
            task_name="Paper Billing Failure",
            status="pending",
        )
        task.resource_files.add(file_record)

        result = run_paper_detection(task.id)

        task.refresh_from_db()
        self.assertIn("额度/计费不可用", result)
        self.assertEqual(task.status, "failed")
        self.assertIn("额度/计费不可用", task.error_message)
        self.assertEqual(mock_post.call_count, 1)
        mock_image_detection.assert_not_called()

    def test_preprocess_document_extracts_text_from_pdf_when_pymupdf_is_available(self):
        file_record = self.create_pdf_file("paper.pdf", "PDF parsing should work for task creation and execution.")
        file_path = self.temp_media / file_record.stored_path

        result = preprocess_document(str(file_path))

        self.assertIn("PDF parsing should work", result["text_content"])
        self.assertGreaterEqual(len(result["segments"]), 1)
        self.assertGreaterEqual(len(result["paragraphs"]), 1)

    def test_extract_pdf_tables_infers_table_like_aligned_text(self):
        file_record = self.create_table_like_pdf_file("paper-table-like.pdf")
        file_path = self.temp_media / file_record.stored_path

        tables = extract_pdf_tables(str(file_path))

        self.assertGreaterEqual(len(tables), 1)
        self.assertEqual(tables[0]["source"], "pdf_inferred")
        self.assertIn("Accuracy", tables[0]["text"])
        self.assertIn("91.4", tables[0]["text"])

    @patch("core.services.orchestrators.paper_task_orchestrator.run_image_detection_task")
    @patch("core.services.capabilities.data_authenticity_service.summarize_data_authenticity")
    @patch("core.services.capabilities.data_authenticity_service.assess_table_authenticity")
    @patch("core.services.capabilities.data_authenticity_service.assess_data_authenticity_finding")
    @patch("core.services.capabilities.llm.fastdetect_client.requests.post")
    def test_run_paper_detection_keeps_table_analysis_separate_from_aigc_segments(
        self,
        mock_post,
        mock_assess_data,
        mock_assess_table,
        mock_summary,
        mock_image_detection,
    ):
        mock_post.return_value.json.return_value = {"data": {"prob": 0.18, "details": {"source": "mock"}}}
        mock_post.return_value.raise_for_status.return_value = None
        mock_assess_data.return_value = {"risk_level": "none", "reason": "paragraph has no data claim"}
        mock_assess_table.return_value = {"risk_level": "low", "reason": "table values are internally consistent"}
        mock_summary.return_value = {
            "risk_level": "low",
            "summary": "LLM summary confirms table-like data was analyzed separately.",
            "key_points": ["table extracted"],
        }
        file_record = self.create_table_like_pdf_file("paper-with-table-like-data.pdf")
        task = DetectionTask.objects.create(
            user=self.user,
            organization=self.organization,
            task_type="paper",
            task_name="Paper With Inferred Table",
            status="pending",
        )
        task.resource_files.add(file_record)

        result = run_paper_detection(task.id)

        task.refresh_from_db()
        self.assertEqual(result, "Paper detection finished")
        self.assertEqual(task.status, "completed")
        self.assertGreaterEqual(task.text_detection_results["document"]["table_count"], 1)
        self.assertGreaterEqual(len(task.text_detection_results["table_results"]), 1)
        paragraph_text = "\n".join(item.get("text", "") for item in task.text_detection_results["paragraph_results"])
        self.assertNotIn("Accuracy", paragraph_text)
        self.assertNotIn("91.4", paragraph_text)
        self.assertEqual(mock_assess_data.call_count, len(task.text_detection_results["paragraph_results"]))
        self.assertEqual(mock_assess_table.call_count, len(task.text_detection_results["table_results"]))
        self.assertEqual(task.text_detection_results["data_authenticity_results"]["summary_source"], "llm")
        mock_image_detection.assert_not_called()

    def test_preprocess_document_removes_null_bytes_from_pdf_text(self):
        file_record = self.create_pdf_file("paper-null.pdf", "Null\x00byte should not reach JSON storage.")
        file_path = self.temp_media / file_record.stored_path

        result = preprocess_document(str(file_path))

        self.assertNotIn("\x00", result["text_content"])
        self.assertTrue(all("\x00" not in segment for segment in result["segments"]))
        self.assertTrue(all("\x00" not in paragraph for paragraph in result["paragraphs"]))

    def test_extract_document_paragraphs_merges_soft_wrapped_lines_within_same_paragraph(self):
        text = (
            "This is a long paragraph line that was wrapped by the source document\n"
            "but should still stay in the same paragraph after preprocessing\n"
            "It continues here on a third line.\n\n"
            "This is the second real paragraph."
        )

        paragraphs = extract_document_paragraphs(text)

        self.assertEqual(len(paragraphs), 2)
        self.assertEqual(
            paragraphs[0],
            (
                "This is a long paragraph line that was wrapped by the source document "
                "but should still stay in the same paragraph after preprocessing "
                "It continues here on a third line."
            ),
        )
        self.assertEqual(paragraphs[1], "This is the second real paragraph.")

    def test_extract_document_paragraphs_keeps_reference_items_as_separate_paragraphs(self):
        text = (
            "References\n"
            "[1] First reference entry\n"
            "continued on the next line\n"
            "[2] Second reference entry"
        )

        paragraphs = extract_document_paragraphs(text)

        self.assertEqual(
            paragraphs,
            [
                "References",
                "[1] First reference entry continued on the next line",
                "[2] Second reference entry",
            ],
        )

    @patch("core.services.orchestrators.paper_task_orchestrator.run_image_detection_task")
    @patch("core.services.capabilities.llm.fastdetect_client.requests.post")
    def test_run_paper_detection_handles_missing_decodable_text(self, mock_post, mock_image_detection):
        mock_post.return_value.json.return_value = {"data": {"prob": 0.1, "details": {}}}
        mock_post.return_value.raise_for_status.return_value = None
        uploads_dir = self.temp_media / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        file_path = uploads_dir / "paper.bin"
        file_path.write_bytes(b"\xff\xfe\x00\xff")
        file_record = FileManagement.objects.create(
            user=self.user,
            organization=self.organization,
            file_name="paper.bin",
            file_size=file_path.stat().st_size,
            file_type="application/octet-stream",
            resource_type="paper",
            stored_path="uploads/paper.bin",
        )
        task = DetectionTask.objects.create(
            user=self.user,
            organization=self.organization,
            task_type="paper",
            task_name="Unreadable Paper",
            status="pending",
        )
        task.resource_files.add(file_record)

        run_paper_detection(task.id)

        task.refresh_from_db()
        self.assertEqual(task.status, "completed")
        self.assertEqual(len(task.text_detection_results["paragraph_results"]), 1)
        self.assertTrue(task.text_detection_results["paragraph_results"][0]["text"])
        self.assertEqual(task.text_detection_results["reference_results"], [])
        self.assertEqual(task.paper_detection_result.reference_results.count(), 0)
        mock_image_detection.assert_not_called()

    @patch("core.services.orchestrators.paper_task_orchestrator.run_image_detection_task")
    @patch("core.services.capabilities.reference_check_service.assess_reference_authenticity")
    @patch("core.services.capabilities.llm.fastdetect_client.requests.post")
    def test_run_paper_detection_accepts_authenticity_score_reference_payload(
        self,
        mock_post,
        mock_assess_reference_authenticity,
        mock_image_detection,
    ):
        mock_post.return_value.json.return_value = {"data": {"prob": 0.18, "details": {"source": "mock"}}}
        mock_post.return_value.raise_for_status.return_value = None
        mock_assess_reference_authenticity.return_value = {
            "authenticity_score": 0.91,
            "authenticity_label": "likely_real",
            "authenticity_reason": "Reference metadata looks internally consistent.",
        }
        file_record = self.create_text_file(
            "paper-with-references.txt",
            "Abstract\nA short abstract paragraph.\nReferences\n[1] Example reference entry.",
        )
        task = DetectionTask.objects.create(
            user=self.user,
            organization=self.organization,
            task_type="paper",
            task_name="Paper With References",
            status="pending",
        )
        task.resource_files.add(file_record)

        result = run_paper_detection(task.id)

        task.refresh_from_db()
        self.assertEqual(result, "Paper detection finished")
        self.assertEqual(task.status, "completed")
        self.assertEqual(task.error_message, "")
        self.assertEqual(len(task.text_detection_results["reference_results"]), 1)
        self.assertEqual(task.text_detection_results["reference_results"][0]["authenticity_score"], 0.91)
        self.assertEqual(task.text_detection_results["reference_results"][0]["authenticity_label"], "likely_real")
        self.assertEqual(task.paper_detection_result.reference_results.count(), 1)
        mock_image_detection.assert_not_called()

    @patch("core.services.capabilities.review_analysis_service.analyze_review_text")
    def test_run_review_detection_returns_relevance_matches(self, mock_analyze_review_text):
        mock_analyze_review_text.return_value = {
            "overall": {
                "template_like_level": "low",
                "wrongness_level": "low",
                "relevance_level": "high",
                "summary": "Relevant review",
                "key_findings": [],
                "suggestions": [],
            },
            "paragraph_results": [
                {
                    "review_paragraph_index": 0,
                    "paper_paragraph_index": 0,
                    "template_like_level": "low",
                    "wrongness_level": "low",
                    "relevance_score": 0.78,
                    "relevance_level": "high",
                    "explanation": "Matches the paper.",
                }
            ],
        }
        paper_file = self.create_review_file(
            "review-paper.txt",
            "Alpha beta gamma findings.\nReferences\n[1] Alpha beta source.",
            resource_type="review_paper",
        )
        review_file = self.create_review_file(
            "review-comment.txt",
            "Alpha beta needs more evidence.",
            resource_type="review_file",
            linked_file=paper_file,
        )
        task = DetectionTask.objects.create(
            user=self.user,
            organization=self.organization,
            task_type="review",
            task_name="Review Detection",
            status="pending",
        )
        task.resource_files.add(paper_file, review_file)

        result = run_review_detection(task.id)

        task.refresh_from_db()
        self.assertEqual(result, "Review detection finished")
        self.assertEqual(task.status, "completed")
        self.assertEqual(len(task.text_detection_results["paragraph_results"]), 1)
        self.assertEqual(len(task.text_detection_results["relevance_results"]), 1)
        self.assertEqual(task.text_detection_results["relevance_results"][0]["paper_paragraph_index"], 0)
        self.assertTrue(ReviewDetectionResult.objects.filter(detection_task=task).exists())
        self.assertEqual(task.review_detection_result.paragraph_results.count(), 1)

    @patch("core.services.capabilities.llm.fastdetect_client.requests.post")
    def test_run_review_detection_aggregates_multiple_review_pairs_into_items(self, mock_post):
        mock_post.return_value.json.return_value = {"data": {"prob": 0.34, "details": {"source": "mock"}}}
        mock_post.return_value.raise_for_status.return_value = None
        paper_file_1 = self.create_review_file(
            "review-paper-1.txt",
            "Paper one content.",
            resource_type="review_paper",
        )
        review_file_1 = self.create_review_file(
            "review-comment-1.txt",
            "Review one content.",
            resource_type="review_file",
            linked_file=paper_file_1,
        )
        paper_file_2 = self.create_review_file(
            "review-paper-2.txt",
            "Paper two content.",
            resource_type="review_paper",
        )
        review_file_2 = self.create_review_file(
            "review-comment-2.txt",
            "Review two content.",
            resource_type="review_file",
            linked_file=paper_file_2,
        )
        task = DetectionTask.objects.create(
            user=self.user,
            organization=self.organization,
            task_type="review",
            task_name="Multi Review Detection",
            status="pending",
        )
        task.resource_files.add(paper_file_1, review_file_1, paper_file_2, review_file_2)

        result = run_review_detection(task.id)

        task.refresh_from_db()
        self.assertEqual(result, "Review detection finished")
        self.assertEqual(task.status, "completed")
        self.assertEqual(task.text_detection_results["document"]["resource_count"], 2)
        self.assertEqual(len(task.text_detection_results["items"]), 2)
        self.assertEqual(task.text_detection_results["items"][0]["document"]["paper_file_name"], "review-paper-1.txt")
        self.assertEqual(task.text_detection_results["items"][1]["document"]["paper_file_name"], "review-paper-2.txt")
        self.assertEqual(task.text_detection_results["document"]["paper_file_name"], "review-paper-1.txt")

    def test_task_compatibility_wrappers_are_plain_functions_without_celery_delay(self):
        self.assertFalse(hasattr(run_paper_detection, "delay"))
        self.assertFalse(hasattr(run_review_detection, "delay"))

    def test_sanitize_json_like_removes_null_bytes_recursively(self):
        payload = {
            "document": {"file_name": "bad\x00name.pdf"},
            "paragraph_results": [{"text": "abc\x00def", "details": {"reason": "x\x00y"}}],
            "list": ["ok\x00", 1, None],
        }

        sanitized = sanitize_json_like(payload)

        self.assertEqual(sanitized["document"]["file_name"], "badname.pdf")
        self.assertEqual(sanitized["paragraph_results"][0]["text"], "abcdef")
        self.assertEqual(sanitized["paragraph_results"][0]["details"]["reason"], "xy")
        self.assertEqual(sanitized["list"][0], "ok")

    @patch("core.services.capabilities.llm_analysis_service.summarize_paper_overall")
    def test_overall_paper_evaluation_escalates_confirmed_ai_and_high_risk_reference(self, mock_summary):
        mock_summary.return_value = {
            "risk_level": "low",
            "summary": "LLM returned a lower risk level.",
            "key_concerns": [],
            "suggestions": [],
        }
        paragraph_results = [
            {"paragraph_index": 0, "label": "suspicious", "probability": 0.91},
            {"paragraph_index": 1, "label": "suspicious", "probability": 0.88},
            {"paragraph_index": 2, "label": "suspicious", "probability": 0.66},
            {"paragraph_index": 3, "label": "clean", "probability": 0.12},
        ]
        confirmed_ai_paragraphs = paragraph_results[:2]
        reference_results = [{"reference_index": 0, "authenticity_label": "high_risk"}]

        evaluation = build_overall_paper_evaluation(
            paragraph_results=paragraph_results,
            confirmed_ai_paragraphs=confirmed_ai_paragraphs,
            reference_results=reference_results,
            data_authenticity_results={"findings": []},
        )

        self.assertEqual(evaluation["risk_level"], "high")
        self.assertGreaterEqual(evaluation["risk_score"], 70)
        self.assertEqual(evaluation["summary_source"], "rule_based")

    def test_fastdetect_runtime_config_prefers_active_database_config(self):
        LLMModel.objects.create(
            model_name="fast-detect-db",
            display_name="FastDetect DB",
            provider="fastdetect",
            model_type="fastdetect",
            endpoint="https://example.test/api/detect",
            api_key="db-key",
            is_active=True,
        )

        config = get_fastdetect_runtime_config()

        self.assertEqual(config["endpoint"], "https://example.test/api/detect")
        self.assertEqual(config["model"], "fast-detect-db")
        self.assertEqual(config["key"], "db-key")
