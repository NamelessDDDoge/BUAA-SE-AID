"""5.12 SubDetectionResult 表"""
import pytest
from django.db import IntegrityError
from django.test import override_settings

from core.models import SubDetectionResult
from core.tests.factories import make_detection_result

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@override_settings(MEDIA_ROOT="/tmp/test-media-sub")
def test_str_contains_method_and_detection_result_id():
    dr = make_detection_result()
    sub = SubDetectionResult.objects.create(
        detection_result=dr, method="method1", probability=0.5, mask_matrix=[[0]],
    )
    rendered = str(sub)
    assert "method1" in rendered
    assert str(dr.id) in rendered


@override_settings(MEDIA_ROOT="/tmp/test-media-sub")
def test_one_method_per_detection_result_is_unique():
    dr = make_detection_result()
    SubDetectionResult.objects.create(
        detection_result=dr, method="method3", probability=0.1, mask_matrix=[[0]],
    )
    with pytest.raises(IntegrityError):
        SubDetectionResult.objects.create(
            detection_result=dr, method="method3", probability=0.2, mask_matrix=[[0]],
        )


@override_settings(MEDIA_ROOT="/tmp/test-media-sub")
def test_all_seven_methods_can_attach_to_one_detection_result():
    dr = make_detection_result()
    for i in range(1, 8):
        SubDetectionResult.objects.create(
            detection_result=dr, method=f"method{i}", probability=0.1 * i, mask_matrix=[[i]],
        )
    assert dr.sub_results.count() == 7


@override_settings(MEDIA_ROOT="/tmp/test-media-sub")
def test_mask_matrix_supports_nested_list():
    matrix = [[0.0, 0.1], [0.2, 0.3]]
    dr = make_detection_result()
    sub = SubDetectionResult.objects.create(
        detection_result=dr, method="method2", probability=0.42, mask_matrix=matrix,
    )
    sub.refresh_from_db()
    assert sub.mask_matrix == matrix
    assert sub.probability == pytest.approx(0.42)
