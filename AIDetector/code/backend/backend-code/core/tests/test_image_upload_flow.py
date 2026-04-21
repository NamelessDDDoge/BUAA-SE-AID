import shutil
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import FileManagement, ImageUpload, Organization, User


def build_uploaded_file(name, content_type="image/png", color=(255, 0, 0), payload=b"sample"):
    if content_type.startswith("image/"):
        buffer = BytesIO()
        Image.new("RGB", (12, 12), color=color).save(buffer, format="PNG")
        payload = buffer.getvalue()
    return SimpleUploadedFile(name, payload, content_type=content_type)


def build_zip_uploaded_file(name="bundle.zip"):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as archive:
        image_buffer = BytesIO()
        Image.new("RGB", (10, 10), color=(0, 255, 0)).save(image_buffer, format="PNG")
        archive.writestr("folder/inside.png", image_buffer.getvalue())
        archive.writestr("notes.txt", b"ignore me")
    return SimpleUploadedFile(name, zip_buffer.getvalue(), content_type="application/zip")


def build_pdf_uploaded_file(name="paper-images.pdf", payload=b"%PDF-1.4 fake image bundle"):
    return SimpleUploadedFile(name, payload, content_type="application/pdf")


@override_settings(ENABLE_FANYI=False)
class UploadFileFlowTests(TestCase):
    def setUp(self):
        temp_root = Path.home() / ".codex" / "memories" / "buaa-se-aid-upload-tests"
        shutil.rmtree(temp_root, ignore_errors=True)
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_media = str(temp_root)
        self.override = override_settings(MEDIA_ROOT=self.temp_media)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(lambda: shutil.rmtree(self.temp_media, ignore_errors=True))

        self.client = APIClient()
        self.organization = Organization.objects.create(name="Upload Org", email="upload-org@example.com")
        self.user = User.objects.create_user(
            username="upload-user",
            email="upload-user@example.com",
            password="pass123456",
            role="publisher",
            organization=self.organization,
        )
        self.client.force_authenticate(self.user)

    def test_upload_image_file_extracts_single_image_and_marks_image_resource_type(self):
        response = self.client.post(
            "/api/upload/",
            {
                "detection_type": "image",
                "file": build_uploaded_file("image.png"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        file_record = FileManagement.objects.get(pk=response.data["file_id"])
        self.assertEqual(file_record.resource_type, "image")
        self.assertEqual(ImageUpload.objects.filter(file_management=file_record).count(), 1)

    def test_upload_image_with_long_filename_keeps_image_path_within_model_limit(self):
        long_name = f"{'a' * 70}.png"
        response = self.client.post(
            "/api/upload/",
            {
                "detection_type": "image",
                "file": build_uploaded_file(long_name),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        image_upload = ImageUpload.objects.get(file_management_id=response.data["file_id"])
        max_length = ImageUpload._meta.get_field("image").max_length
        self.assertLessEqual(len(image_upload.image.name), max_length)

    def test_upload_paper_file_creates_paper_resource_without_extracting_images(self):
        response = self.client.post(
            "/api/upload/",
            {
                "detection_type": "paper",
                "file": build_uploaded_file("paper.pdf", content_type="application/pdf", payload=b"%PDF-1.4 test"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        file_record = FileManagement.objects.get(pk=response.data["file_id"])
        self.assertEqual(file_record.resource_type, "paper")
        self.assertEqual(ImageUpload.objects.filter(file_management=file_record).count(), 0)

    def test_upload_image_zip_extracts_embedded_images_only(self):
        response = self.client.post(
            "/api/upload/",
            {
                "detection_type": "image",
                "file": build_zip_uploaded_file(),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        file_record = FileManagement.objects.get(pk=response.data["file_id"])
        extracted_images = ImageUpload.objects.filter(file_management=file_record)
        self.assertEqual(extracted_images.count(), 1)
        self.assertFalse(extracted_images.get().extracted_from_pdf)

    @patch("core.services.resources.upload_service.create_image_uploads_for_resource")
    def test_upload_image_pdf_is_accepted_and_delegates_to_extraction_service(self, mock_extract):
        response = self.client.post(
            "/api/upload/",
            {
                "detection_type": "image",
                "file": build_pdf_uploaded_file(),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        file_record = FileManagement.objects.get(pk=response.data["file_id"])
        self.assertEqual(file_record.resource_type, "image")
        mock_extract.assert_called_once_with(file_record)

    def test_upload_review_paper_sets_review_paper_resource_type(self):
        response = self.client.post(
            "/api/upload/",
            {
                "detection_type": "review",
                "review_role": "paper",
                "file": build_uploaded_file("review-paper.pdf", content_type="application/pdf", payload=b"%PDF-1.4 review"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        file_record = FileManagement.objects.get(pk=response.data["file_id"])
        self.assertEqual(file_record.resource_type, "review_paper")
        self.assertIsNone(file_record.linked_file)

    def test_upload_review_file_requires_linked_review_paper(self):
        response = self.client.post(
            "/api/upload/",
            {
                "detection_type": "review",
                "review_role": "review",
                "file": build_uploaded_file("review.txt", content_type="text/plain", payload=b"review text"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["message"], "Review upload must include linked_paper_file_id")

    def test_upload_review_file_links_to_review_paper_file(self):
        review_paper_response = self.client.post(
            "/api/upload/",
            {
                "detection_type": "review",
                "review_role": "paper",
                "file": build_uploaded_file("review-paper.pdf", content_type="application/pdf", payload=b"%PDF-1.4 linked"),
            },
            format="multipart",
        )
        review_paper_id = review_paper_response.data["file_id"]

        response = self.client.post(
            "/api/upload/",
            {
                "detection_type": "review",
                "review_role": "review",
                "linked_paper_file_id": review_paper_id,
                "file": build_uploaded_file("review.txt", content_type="text/plain", payload=b"review body"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        review_file = FileManagement.objects.get(pk=response.data["file_id"])
        self.assertEqual(review_file.resource_type, "review_file")
        self.assertEqual(review_file.linked_file_id, review_paper_id)
