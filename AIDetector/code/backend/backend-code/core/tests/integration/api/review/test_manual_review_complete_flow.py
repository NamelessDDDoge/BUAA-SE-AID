"""DTC-USER-4 Manual Review Complete Flow — expanded coverage"""
import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from core.models import ImageReview, ManualReview, ReviewRequest
from core.tests.factories import (
    make_detection_result,
    make_detection_task,
    make_file_management,
    make_image_upload,
    make_organization,
    make_review_request,
    make_user,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

MEDIA = "/tmp/test-media-complete-flow"


@pytest.fixture
def client():
    return APIClient()


def _make_standard_setup(*, num_reviewers=1, num_images=1):
    """
    Build a complete org + publisher + admin + N reviewers + task + images + review_request.
    Returns a dict of named objects.
    """
    org = make_organization()
    admin = make_user(organization=org, role="admin", is_staff=True)
    publisher = make_user(organization=org, role="publisher")
    reviewers = [make_user(organization=org, role="reviewer") for _ in range(num_reviewers)]

    org.admin_user = admin
    org.save(update_fields=["admin_user"])

    task = make_detection_task(user=publisher, organization=org, task_type="image", status="completed")
    source_files = [
        make_file_management(user=publisher, organization=org, resource_type="image", file_type="image/png")
        for _ in range(num_images)
    ]
    image_uploads = [
        make_image_upload(detection_task=task, file_management=sf)
        for sf in source_files
    ]
    detection_result = make_detection_result(
        detection_task=task,
        image_upload=image_uploads[0],
        status="completed",
        is_fake=True,
        confidence_score=0.87,
    )

    review_request = ReviewRequest.objects.create(
        detection_result=detection_result,
        user=publisher,
        organization=org,
        reason="Please double check",
    )
    for img in image_uploads:
        review_request.imgs.add(img)
    for reviewer in reviewers:
        review_request.reviewers.add(reviewer)

    return {
        "org": org,
        "admin": admin,
        "publisher": publisher,
        "reviewers": reviewers,
        "reviewer": reviewers[0],
        "task": task,
        "image_uploads": image_uploads,
        "image_upload": image_uploads[0],
        "detection_result": detection_result,
        "review_request": review_request,
    }


def _submit_review_payload(image_upload_id, *, final=True):
    """Minimal valid payload for post_review with a single image."""
    return {
        "result": [
            {
                "img_id": image_upload_id,
                "score": [1, 2, 3, 4, 5, 4, 3],
                "reason": ["r1", "r2", "r3", "r4", "r5", "r6", "r7"],
                "points": [[], [], [], [], [], [], []],
                "final": final,
            }
        ]
    }


@override_settings(MEDIA_ROOT=MEDIA)
def test_admin_reject_sets_refused_and_no_manual_reviews_created(client):
    """
    Admin rejects (choice=0):
    - status2 must become "refused"
    - status1 must remain "pending"
    - No ManualReview objects must be created
    """
    ctx = _make_standard_setup(num_reviewers=2, num_images=1)
    review_request = ctx["review_request"]
    admin = ctx["admin"]

    client.force_authenticate(admin)
    resp = client.post(
        f"/api/handle_reviewRequest/{review_request.id}/",
        {"choice": 0, "reason": "insufficient evidence"},
        format="json",
    )

    assert resp.status_code == 200, resp.data

    review_request.refresh_from_db()
    assert review_request.status2 == "refused", (
        f"Expected status2='refused', got '{review_request.status2}'"
    )
    assert review_request.status1 == "pending", (
        f"Expected status1='pending' (unchanged), got '{review_request.status1}'"
    )

    # No ManualReview should be created for a rejected request
    manual_review_count = ManualReview.objects.filter(review_request=review_request).count()
    assert manual_review_count == 0, (
        f"Expected 0 ManualReview objects, found {manual_review_count}"
    )

    # No ImageReview should be created either
    image_review_count = ImageReview.objects.filter(
        manual_review__review_request=review_request
    ).count()
    assert image_review_count == 0, (
        f"Expected 0 ImageReview objects, found {image_review_count}"
    )


@override_settings(MEDIA_ROOT=MEDIA)
def test_admin_accept_creates_manual_review_per_reviewer(client):
    """
    Admin accepts (choice=1) with 3 reviewers and 2 images:
    - status2 == "accepted"
    - status1 == "in_progress"
    - Exactly 3 ManualReview created (one per reviewer)
    - Each ManualReview has exactly 2 imgs linked
    - Each ManualReview has exactly 2 ImageReview records with result=None
    """
    ctx = _make_standard_setup(num_reviewers=3, num_images=2)
    review_request = ctx["review_request"]
    admin = ctx["admin"]
    reviewers = ctx["reviewers"]
    image_uploads = ctx["image_uploads"]

    client.force_authenticate(admin)
    resp = client.post(
        f"/api/handle_reviewRequest/{review_request.id}/",
        {"choice": 1, "reason": "looks good"},
        format="json",
    )

    assert resp.status_code == 200, resp.data

    review_request.refresh_from_db()
    assert review_request.status2 == "accepted"
    assert review_request.status1 == "in_progress"

    manual_reviews = ManualReview.objects.filter(review_request=review_request)
    assert manual_reviews.count() == 3, (
        f"Expected 3 ManualReview (one per reviewer), got {manual_reviews.count()}"
    )

    reviewer_ids_with_manual = set(manual_reviews.values_list("reviewer_id", flat=True))
    expected_reviewer_ids = {r.id for r in reviewers}
    assert reviewer_ids_with_manual == expected_reviewer_ids, (
        f"ManualReview reviewer IDs mismatch: {reviewer_ids_with_manual} vs {expected_reviewer_ids}"
    )

    expected_img_ids = {img.id for img in image_uploads}
    for mr in manual_reviews:
        assert mr.status == "undo"
        actual_img_ids = set(mr.imgs.values_list("id", flat=True))
        assert actual_img_ids == expected_img_ids, (
            f"ManualReview {mr.id}: imgs mismatch {actual_img_ids} vs {expected_img_ids}"
        )

        image_reviews = ImageReview.objects.filter(manual_review=mr)
        assert image_reviews.count() == 2, (
            f"ManualReview {mr.id}: expected 2 ImageReview, got {image_reviews.count()}"
        )
        for ir in image_reviews:
            assert ir.result is None, (
                f"ImageReview {ir.id} should have result=None before submission"
            )


@override_settings(MEDIA_ROOT=MEDIA)
def test_single_reviewer_submit_completes_request(client):
    """
    Single reviewer + single image:
    1. Admin accepts → status1="in_progress"
    2. Reviewer submits → ManualReview.status="completed", ReviewRequest.status1="completed"
    3. ImageUpload.isReview=True, ImageReview.result is set
    """
    ctx = _make_standard_setup(num_reviewers=1, num_images=1)
    review_request = ctx["review_request"]
    admin = ctx["admin"]
    reviewer = ctx["reviewer"]
    image_upload = ctx["image_upload"]

    # Step 1: Admin accepts
    client.force_authenticate(admin)
    resp = client.post(
        f"/api/handle_reviewRequest/{review_request.id}/",
        {"choice": 1, "reason": "approved"},
        format="json",
    )
    assert resp.status_code == 200, resp.data

    manual_review = ManualReview.objects.get(review_request=review_request, reviewer=reviewer)
    assert manual_review.status == "undo"

    # Step 2: Reviewer submits
    client.force_authenticate(reviewer)
    resp = client.post(
        f"/api/post_review/{manual_review.id}/",
        _submit_review_payload(image_upload.id, final=True),
        format="json",
    )
    assert resp.status_code == 201, resp.data

    # Step 3: Verify state transitions
    manual_review.refresh_from_db()
    review_request.refresh_from_db()
    image_upload.refresh_from_db()

    assert manual_review.status == "completed", (
        f"ManualReview.status should be 'completed', got '{manual_review.status}'"
    )
    assert review_request.status1 == "completed", (
        f"ReviewRequest.status1 should be 'completed' (all done), got '{review_request.status1}'"
    )
    assert image_upload.isReview is True

    image_review = ImageReview.objects.get(manual_review=manual_review, img=image_upload)
    assert image_review.result is True
    assert image_review.score1 == 1
    assert image_review.score7 == 3
    assert image_review.reason1 == "r1"


@override_settings(MEDIA_ROOT=MEDIA)
def test_partial_reviewer_completion_keeps_status_in_progress(client):
    """
    2 reviewers:
    - After reviewer-1 submits: status1 == "in_progress" (reviewer-2 not done)
    - After reviewer-2 submits: status1 == "completed"
    """
    ctx = _make_standard_setup(num_reviewers=2, num_images=1)
    review_request = ctx["review_request"]
    admin = ctx["admin"]
    reviewer1, reviewer2 = ctx["reviewers"]
    image_upload = ctx["image_upload"]

    # Admin accepts
    client.force_authenticate(admin)
    resp = client.post(
        f"/api/handle_reviewRequest/{review_request.id}/",
        {"choice": 1, "reason": "approved"},
        format="json",
    )
    assert resp.status_code == 200, resp.data

    mr1 = ManualReview.objects.get(review_request=review_request, reviewer=reviewer1)
    mr2 = ManualReview.objects.get(review_request=review_request, reviewer=reviewer2)

    # Reviewer 1 submits
    client.force_authenticate(reviewer1)
    resp = client.post(
        f"/api/post_review/{mr1.id}/",
        _submit_review_payload(image_upload.id),
        format="json",
    )
    assert resp.status_code == 201, resp.data

    # After only reviewer-1 done: still in_progress
    review_request.refresh_from_db()
    assert review_request.status1 == "in_progress", (
        f"status1 should still be 'in_progress' after only 1 of 2 reviewers done, "
        f"got '{review_request.status1}'"
    )
    mr1.refresh_from_db()
    assert mr1.status == "completed"
    mr2.refresh_from_db()
    assert mr2.status == "undo"

    # Reviewer 2 submits
    client.force_authenticate(reviewer2)
    resp = client.post(
        f"/api/post_review/{mr2.id}/",
        _submit_review_payload(image_upload.id),
        format="json",
    )
    assert resp.status_code == 201, resp.data

    # Now all done: completed
    review_request.refresh_from_db()
    assert review_request.status1 == "completed", (
        f"status1 should be 'completed' after both reviewers done, "
        f"got '{review_request.status1}'"
    )


@override_settings(MEDIA_ROOT=MEDIA)
def test_publisher_detail_shows_correct_done_process_counters(client):
    """
    2 reviewers:
    - Before any submission: done=0, process=2
    - After reviewer-1 submits: done=1, process=1
    - After reviewer-2 submits: done=2, process=0
    Also checks reviewers list entries contain correct status and completed_count.
    """
    ctx = _make_standard_setup(num_reviewers=2, num_images=1)
    review_request = ctx["review_request"]
    admin = ctx["admin"]
    publisher = ctx["publisher"]
    reviewer1, reviewer2 = ctx["reviewers"]
    image_upload = ctx["image_upload"]

    # Admin accepts
    client.force_authenticate(admin)
    resp = client.post(
        f"/api/handle_reviewRequest/{review_request.id}/",
        {"choice": 1, "reason": "approved"},
        format="json",
    )
    assert resp.status_code == 200, resp.data

    mr1 = ManualReview.objects.get(review_request=review_request, reviewer=reviewer1)
    mr2 = ManualReview.objects.get(review_request=review_request, reviewer=reviewer2)

    # --- Stage 0: nothing submitted yet ---
    client.force_authenticate(publisher)
    resp = client.get(f"/api/get_request_detail/{review_request.id}/")
    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == {"done": 0, "process": 2}, (
        f"Before any submission: expected {{done:0, process:2}}, got {resp.data['status']}"
    )
    # Both reviewers show 'undo'
    statuses = {r["username"]: r["status"] for r in resp.data["reviewers"]}
    assert statuses[reviewer1.username] == "undo"
    assert statuses[reviewer2.username] == "undo"

    # --- Stage 1: reviewer-1 submits ---
    client.force_authenticate(reviewer1)
    client.post(
        f"/api/post_review/{mr1.id}/",
        _submit_review_payload(image_upload.id),
        format="json",
    )

    client.force_authenticate(publisher)
    resp = client.get(f"/api/get_request_detail/{review_request.id}/")
    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == {"done": 1, "process": 1}, (
        f"After reviewer-1 done: expected {{done:1, process:1}}, got {resp.data['status']}"
    )
    statuses = {r["username"]: r["status"] for r in resp.data["reviewers"]}
    assert statuses[reviewer1.username] == "completed"
    assert statuses[reviewer2.username] == "undo"
    completed_counts = {r["username"]: r["completed_count"] for r in resp.data["reviewers"]}
    assert completed_counts[reviewer1.username] == 1
    assert completed_counts[reviewer2.username] == 0

    # --- Stage 2: reviewer-2 submits ---
    client.force_authenticate(reviewer2)
    client.post(
        f"/api/post_review/{mr2.id}/",
        _submit_review_payload(image_upload.id),
        format="json",
    )

    client.force_authenticate(publisher)
    resp = client.get(f"/api/get_request_detail/{review_request.id}/")
    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == {"done": 2, "process": 0}, (
        f"After both done: expected {{done:2, process:0}}, got {resp.data['status']}"
    )
    for reviewer_data in resp.data["reviewers"]:
        assert reviewer_data["status"] == "completed"
        assert reviewer_data["completed_count"] == 1


@override_settings(MEDIA_ROOT=MEDIA)
def test_publisher_cannot_access_manual_review_detail(client):
    """
    Publisher tries to call GET /api/get_review_detail/<mr_id>/ — must be 403
    because the view requires role=='reviewer'.
    """
    ctx = _make_standard_setup(num_reviewers=1, num_images=1)
    review_request = ctx["review_request"]
    admin = ctx["admin"]
    publisher = ctx["publisher"]
    reviewer = ctx["reviewer"]

    # Admin accepts, creating ManualReview
    client.force_authenticate(admin)
    resp = client.post(
        f"/api/handle_reviewRequest/{review_request.id}/",
        {"choice": 1, "reason": "approved"},
        format="json",
    )
    assert resp.status_code == 200, resp.data

    manual_review = ManualReview.objects.get(review_request=review_request, reviewer=reviewer)

    # Publisher must not be able to view the reviewer's ManualReview detail
    client.force_authenticate(publisher)
    resp = client.get(f"/api/get_review_detail/{manual_review.id}/")
    assert resp.status_code == 403, (
        f"Publisher accessing get_review_detail should get 403, got {resp.status_code}"
    )


@override_settings(MEDIA_ROOT=MEDIA)
def test_reviewer_cannot_access_other_reviewers_manual_review(client):
    """
    Reviewer-2 tries to call GET /api/get_review_detail/<mr1_id>/ —
    ManualReview.objects.get(id=mr1_id, reviewer=reviewer2) will raise DoesNotExist → 404.
    """
    ctx = _make_standard_setup(num_reviewers=2, num_images=1)
    review_request = ctx["review_request"]
    admin = ctx["admin"]
    reviewer1, reviewer2 = ctx["reviewers"]

    # Admin accepts
    client.force_authenticate(admin)
    resp = client.post(
        f"/api/handle_reviewRequest/{review_request.id}/",
        {"choice": 1, "reason": "approved"},
        format="json",
    )
    assert resp.status_code == 200, resp.data

    mr1 = ManualReview.objects.get(review_request=review_request, reviewer=reviewer1)

    # Reviewer-2 tries to access reviewer-1's ManualReview
    client.force_authenticate(reviewer2)
    resp = client.get(f"/api/get_review_detail/{mr1.id}/")
    assert resp.status_code == 404, (
        f"Reviewer-2 accessing reviewer-1's ManualReview should get 404, got {resp.status_code}"
    )


@override_settings(MEDIA_ROOT=MEDIA)
def test_reviewer_submit_with_wrong_image_id_returns_400(client):
    """
    Reviewer submits a result referencing an image_id that does NOT belong to
    their ManualReview — must get 400.
    """
    ctx = _make_standard_setup(num_reviewers=1, num_images=1)
    review_request = ctx["review_request"]
    admin = ctx["admin"]
    reviewer = ctx["reviewer"]
    publisher = ctx["publisher"]

    # Admin accepts
    client.force_authenticate(admin)
    resp = client.post(
        f"/api/handle_reviewRequest/{review_request.id}/",
        {"choice": 1, "reason": "approved"},
        format="json",
    )
    assert resp.status_code == 200, resp.data

    manual_review = ManualReview.objects.get(review_request=review_request, reviewer=reviewer)

    # Create a second image_upload that belongs to a different task — not in this ManualReview
    unrelated_task = make_detection_task(user=publisher, organization=ctx["org"], task_type="image", status="completed")
    unrelated_file = make_file_management(user=publisher, organization=ctx["org"], resource_type="image", file_type="image/png")
    unrelated_image = make_image_upload(detection_task=unrelated_task, file_management=unrelated_file)

    client.force_authenticate(reviewer)
    resp = client.post(
        f"/api/post_review/{manual_review.id}/",
        _submit_review_payload(unrelated_image.id),
        format="json",
    )

    # Should be rejected because unrelated_image is not in allowed_image_ids
    assert resp.status_code == 400, (
        f"Expected 400 for wrong image_id, got {resp.status_code}. Body: {resp.data}"
    )

    # ManualReview must remain 'undo' — no partial commits
    manual_review.refresh_from_db()
    assert manual_review.status == "undo", (
        f"ManualReview.status should remain 'undo' after failed submission, got '{manual_review.status}'"
    )


@override_settings(MEDIA_ROOT=MEDIA)
def test_admin_accept_twice_creates_duplicate_manual_reviews(client):
    """
    Admin calls handle_reviewRequest twice with choice=1.
    Current implementation: ManualReview.objects.create() is called without get_or_create,
    so a SECOND ManualReview is created for each reviewer on the second call.

    This test documents the ACTUAL current behavior (duplicate creation).
    If the behavior is fixed to be idempotent (get_or_create), update the assertion to count==1.
    """
    ctx = _make_standard_setup(num_reviewers=1, num_images=1)
    review_request = ctx["review_request"]
    admin = ctx["admin"]
    reviewer = ctx["reviewer"]

    client.force_authenticate(admin)

    # First accept
    resp1 = client.post(
        f"/api/handle_reviewRequest/{review_request.id}/",
        {"choice": 1, "reason": "first accept"},
        format="json",
    )
    assert resp1.status_code == 200, resp1.data
    count_after_first = ManualReview.objects.filter(
        review_request=review_request, reviewer=reviewer
    ).count()
    assert count_after_first == 1, (
        f"After first accept: expected 1 ManualReview, got {count_after_first}"
    )

    # Second accept (same request, same admin)
    resp2 = client.post(
        f"/api/handle_reviewRequest/{review_request.id}/",
        {"choice": 1, "reason": "second accept"},
        format="json",
    )
    assert resp2.status_code == 200, resp2.data
    count_after_second = ManualReview.objects.filter(
        review_request=review_request, reviewer=reviewer
    ).count()

    # CURRENT BEHAVIOR: duplicate created — assert 2
    # If this assertion fails after a bug fix, change to: assert count_after_second == 1
    assert count_after_second == 2, (
        f"After second accept (no idempotency guard): expected 2 ManualReview (duplicated), "
        f"got {count_after_second}. "
        f"If the implementation now uses get_or_create, update this assertion to count==1."
    )

    # status fields should still reflect accepted/in_progress
    review_request.refresh_from_db()
    assert review_request.status2 == "accepted"
    assert review_request.status1 == "in_progress"
