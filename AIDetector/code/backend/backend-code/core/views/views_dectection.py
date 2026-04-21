import json
import os
import shutil
import threading

from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from django.conf import settings
from django.db import close_old_connections, transaction
from django.db.models import Q
from django.db.models.fields.files import FieldFile
from ..models import DetectionResult, ImageUpload, Log, User, DetectionTask, FileManagement
from datetime import datetime, timedelta
from django.core.paginator import Paginator


def _refund_detection_usage(organization, if_use_llm, num_images):
    if organization is None or num_images <= 0:
        return
    if if_use_llm:
        organization.add_llm_uses(num_images)
    else:
        organization.add_non_llm_uses(num_images)


def _mark_detection_task_failed(detection_task, error_message):
    DetectionResult.objects.filter(
        detection_task=detection_task,
        status='in_progress',
    ).update(status='failed')
    detection_task.status = 'failed'
    detection_task.error_message = error_message[:2000]
    detection_task.completion_time = timezone.now()
    detection_task.save(update_fields=['status', 'error_message', 'completion_time'])


def _run_detection_task_async(task_id, image_ids, if_use_llm, num_images):
    close_old_connections()
    try:
        detection_task = DetectionTask.objects.select_related('organization').get(pk=task_id)
        image_uploads = list(
            ImageUpload.objects.filter(id__in=image_ids, file_management__user=detection_task.user).order_by('id')
        )
        if not image_uploads:
            raise RuntimeError('No valid images found')
        execute_detection_task(detection_task, image_uploads)
    except Exception as exc:
        detection_task = DetectionTask.objects.select_related('organization').filter(pk=task_id).first()
        if detection_task is not None:
            _refund_detection_usage(detection_task.organization, if_use_llm, num_images)
            _mark_detection_task_failed(detection_task, str(exc))
    finally:
        close_old_connections()


def _start_detection_task_thread(task_id, image_ids, if_use_llm, num_images):
    thread = threading.Thread(
        target=_run_detection_task_async,
        args=(task_id, image_ids, if_use_llm, num_images),
        daemon=True,
        name=f'detection-task-{task_id}',
    )
    thread.start()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_detection_result(request, image_id):
    try:
        # 鑾峰彇妫€娴嬬粨鏋?
        detection_result = DetectionResult.objects.get(image_upload_id=image_id,
                                                       image_upload__file_management__user=request.user)

        # 妫€鏌ョ姸鎬佸苟杩斿洖鐩稿簲鏁版嵁
        if detection_result.status == 'failed':
            return Response({
                "image_id": detection_result.image_upload.id,
                "status": "检测失败",
                "message": detection_result.detection_task.error_message or "AI detection failed.",
            }, status=500)

        if detection_result.status == 'in_progress':
            return Response({
                "image_id": detection_result.image_upload.id,
                "status": "姝ｅ湪妫€娴嬩腑",
                "message": "AI detection is still running. Please check back later.",
            })

        # 濡傛灉妫€娴嬪凡瀹屾垚
        return Response({
            "image_id": detection_result.image_upload.id,
            "status": "妫€娴嬪凡瀹屾垚",
            "is_fake": detection_result.is_fake,
            "confidence_score": detection_result.confidence_score,
            "detection_time": timezone.localtime(detection_result.detection_time)
        })

    except DetectionResult.DoesNotExist:
        return Response({"message": "Detection result not found"}, status=404)


from ..local_detection import execute_detection_task


# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def submit_detection(request):
#     user_id = request.user.id
#     user = User.objects.get(id=user_id)
#     if not user.has_permission('submit'):
#         return Response({"閿欒": "璇ョ敤鎴锋病鏈夋彁浜ゆ娴嬬殑鏉冮檺"}, status=403)
#
#     # 鑾峰彇鐢ㄦ埛鎻愪氦鐨勫浘鍍廔D鍒楄〃
#     image_ids = request.data.get('image_ids', [])
#     task_name = request.data.get('task_name', 'New Detection Task')  # 浠庤姹備腑鑾峰彇浠诲姟鍚嶇О锛岄粯璁や负 "New Detection Task"
#
#     # 鑾峰彇棰濆鐨勫弬鏁?
#     cmd_block_size = request.data.get('cmd_block_size', 64)  # 榛樿涓?4
#     urn_k = request.data.get('urn_k', 0.3)  # 榛樿涓?.3
#     if_use_llm = request.data.get('if_use_llm', False)  # 榛樿涓篎alse
#
#     if not image_ids:
#         return Response({"message": "No image IDs provided"}, status=400)
#
#     # 鏌ユ壘鐢ㄦ埛涓婁紶鐨勬墍鏈夊浘鍍?
#     image_uploads = ImageUpload.objects.filter(id__in=image_ids, file_management__user=request.user)
#
#     # 妫€楠屼笉涓虹┖
#     if not image_uploads.exists():
#         return Response({"message": "No valid images found"}, status=404)
#
#     # 鍒涘缓涓€涓柊鐨勬娴嬩换鍔?
#     detection_task = DetectionTask.objects.create(
#         organization=user.organization,
#         user=request.user,
#         task_name=task_name,  # 浣跨敤鐢ㄦ埛鎻愪氦鐨勪换鍔″悕绉?
#         status='pending',  # 鍒濆鐘舵€佷负"鎺掗槦涓?
#         cmd_block_size=cmd_block_size,
#         urn_k=urn_k,
#         if_use_llm=if_use_llm
#     )
#
#     # 鍦↙og琛ㄤ腑璁板綍妫€娴嬩换鍔＄殑鍒涘缓
#     Log.objects.create(
#         user=request.user,
#         operation_type='detection',
#         related_model='DetectionTask',
#         related_id=detection_task.id
#     )
#
#     # 瀵规瘡涓浘鍍忕敓鎴愭娴嬭褰曪紝骞跺皢鐘舵€佽缃负"姝ｅ湪妫€娴嬩腑"
#     for image_upload in image_uploads:
#         detection_result, created = DetectionResult.objects.get_or_create(
#             image_upload=image_upload,
#             detection_task=detection_task,  # 灏嗕换鍔′笌妫€娴嬬粨鏋滃叧鑱?
#             defaults={'status': 'in_progress'}
#         )
#
#         if not created:
#             detection_result.status = 'in_progress'
#             detection_result.save()
#
#         # 鎻愪氦AI妫€娴嬩换鍔＄粰Celery锛屼紶閫掑弬鏁?
#         run_ai_detection.delay(detection_result.id, cmd_block_size, urn_k, if_use_llm)
#
#     return Response({
#         "message": "Detection request submitted successfully",
#         "task_id": detection_task.id,
#         "task_name": detection_task.task_name,  # 杩斿洖浠诲姟鍚嶇О
#     })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_detection2(request):
    user_id = request.user.id
    mode = int(request.data['mode'])
    user = User.objects.get(id=user_id)
    organization = user.organization  # 鑾峰彇鐢ㄦ埛鎵€灞炵粍缁?
    organization.reset_usage()  # 閲嶇疆缁勭粐鍐呮墍鏈夌敤鎴风殑鍏变韩娆℃暟
    if not user.has_permission('submit'):
        return Response({"閿欒": "璇ョ敤鎴锋病鏈夋彁浜ゆ娴嬬殑鏉冮檺"}, status=403)

    # 鑾峰彇鐢ㄦ埛鎻愪氦鐨勫浘鍍廔D鍒楄〃
    image_ids = request.data.get('image_ids', [])
    image_ids.sort()
    task_name = request.data.get('task_name', 'New Detection Task')  # 浠庤姹備腑鑾峰彇浠诲姟鍚嶇О锛岄粯璁や负 "New Detection Task"

    # 鑾峰彇棰濆鐨勫弬鏁?
    cmd_block_size = request.data.get('cmd_block_size', 64)  # 榛樿涓?4
    urn_k = request.data.get('urn_k', 0.3)  # 榛樿涓?.3
    if_use_llm = request.data.get('if_use_llm', False)  # 榛樿涓篎alse
    method_switches = request.data.get('method_switches')
    if method_switches is not None:
        if not isinstance(method_switches, dict):
            return Response({"message": "method_switches must be an object"}, status=400)
        method_switches = {str(key): bool(value) for key, value in method_switches.items()}
    if mode == 3:
        if_use_llm = True

    if not image_ids:
        return Response({"message": "No image IDs provided"}, status=400)

    # 鏌ユ壘鐢ㄦ埛涓婁紶鐨勬墍鏈夊浘鍍?
    image_uploads = ImageUpload.objects.filter(id__in=image_ids, file_management__user=request.user)

    # 妫€楠屼笉涓虹┖
    if not image_uploads.exists():
        return Response({"message": "No valid images found"}, status=404)

    num_images = len(image_uploads)
    # 妫€鏌ュ墿浣欐鏁版槸鍚﹁冻澶?
    if if_use_llm:
        if not organization.can_use_llm(num_images):
            return Response({
                                "message": f"You have exceeded your LLM method usage limit for this week. Your organization can only submit {organization.remaining_llm_uses} more images."},
                            status=400)
        # 浣跨敤 LLM 鏂规硶鏃讹紝鍑忓皯缁勭粐鐨?LLM 鏂规硶鍓╀綑娆℃暟
        organization.decrement_llm_uses(num_images)
    else:
        if not organization.can_use_non_llm(num_images):
            return Response({
                                "message": f"You have exceeded your non-LLM method usage limit for this week. Your organization can only submit {organization.remaining_non_llm_uses} more images."},
                            status=400)
        # 浣跨敤闈?LLM 鏂规硶鏃讹紝鍑忓皯缁勭粐鐨勯潪 LLM 鏂规硶鍓╀綑娆℃暟
        organization.decrement_non_llm_uses(num_images)

    image_upload_list = list(image_uploads.order_by('id'))

    with transaction.atomic():
        detection_task = DetectionTask.objects.create(
            organization=user.organization,
            user=request.user,
            task_type='image',
            task_name=task_name,
            status='in_progress',
            cmd_block_size=cmd_block_size,
            urn_k=urn_k,
            if_use_llm=if_use_llm,
            method_switches=method_switches,
        )
        detection_task.resource_files.add(*list({img.file_management for img in image_upload_list}))

        DetectionResult.objects.bulk_create([
            DetectionResult(
                image_upload=image_upload,
                detection_task=detection_task,
                status='in_progress',
            )
            for image_upload in image_upload_list
        ])

        Log.objects.create(
            user=request.user,
            operation_type='detection',
            related_model='DetectionTask',
            related_id=detection_task.id
        )

        transaction.on_commit(
            lambda: _start_detection_task_thread(detection_task.id, image_ids, if_use_llm, num_images)
        )

    return Response({
        "message": "Detection request submitted successfully",
        "task_id": detection_task.id,
        "task_name": detection_task.task_name,
        "status": detection_task.status,
        "execution_mode": "local_async",
    })


import os
from django.http import FileResponse
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


from ..utils.report_generator import generate_detection_task_report

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_task_report(request, task_id):
    """
    GET /api/tasks/<task_id>/report/
    涓嬭浇妫€娴嬫姤鍛?PDF
    """
    try:
        task = DetectionTask.objects.get(id=task_id, user=request.user)
        # generate_detection_task_report(task)
    except DetectionTask.DoesNotExist:
        return Response({"detail": "Task not found."}, status=404)

    if task.status != "completed":
        return Response({"detail": "Task not completed yet."}, status=400)

    if not task.report_file:
        # generate_detection_task_report(task)
        return Response({"detail": "Report is still being generated."}, status=202)

    abs_path = os.path.join(settings.MEDIA_ROOT, task.report_file.name)
    if not os.path.exists(abs_path):
        return Response({"detail": "Report file missing."}, status=410)

    return FileResponse(open(abs_path, "rb"),
                        as_attachment=True,
                        filename=f"task_{task.id}_report.pdf")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def image2dr(request, image_id):
    """
    GET /api/images/<image_id>/getdr/
    涓嬭浇璇ュ浘鐗囧搴斾换鍔＄殑妫€娴嬫姤鍛?PDF
    """
    try:
        detection_result = DetectionResult.objects.select_related('detection_task').get(
            image_upload_id=image_id,
        )
    except DetectionResult.DoesNotExist:
        return Response({"detail": "Image or task not found, or permission denied."}, status=404)
    except DetectionResult.MultipleObjectsReturned:
        return Response({"detail": "Multiple detection results found for this image."}, status=500)
    # 杩斿洖detection_result鐨刬d
    return Response({"detection_result_id": detection_result.id})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_image_report(request, image_id):
    """
    GET /api/images/<image_id>/report/
    涓嬭浇璇ュ浘鐗囧搴斾换鍔＄殑妫€娴嬫姤鍛?PDF
    """
    try:
        # 鑾峰彇涓巌mage_id鍏宠仈涓斿睘浜庡綋鍓嶇敤鎴风殑DetectionResult鍙婂叾鍏宠仈鐨凞etectionTask
        detection_result = DetectionResult.objects.select_related('detection_task').get(
            image_upload_id=image_id,
            # detection_task__user=request.user
        )
    except DetectionResult.DoesNotExist:
        return Response({"detail": "Image or task not found, or permission denied."}, status=404)
    except DetectionResult.MultipleObjectsReturned:
        return Response({"detail": "Multiple detection results found for this image."}, status=500)

    task = detection_result.detection_task

    # 鍚庣画閫昏緫涓庡師鎺ュ彛涓€鑷达紝妫€鏌ヤ换鍔＄姸鎬佸拰鎶ュ憡鏂囦欢
    if task.status != "completed":
        return Response({"detail": "Task not completed yet."}, status=400)

    if not task.report_file:
        return Response({"detail": "Report is still being generated."}, status=202)

    abs_path = os.path.join(settings.MEDIA_ROOT, task.report_file.name)
    if not os.path.exists(abs_path):
        return Response({"detail": "Report file missing."}, status=410)

    return FileResponse(open(abs_path, "rb"),
                        as_attachment=True,
                        filename=f"task_{task.id}_report.pdf")


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from ..utils.serializers_safe import serialize_value

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_task_results(request, task_id):
    """
    ?include_image=1   鈥斺€?棰濆杩斿洖鍘熷鍥惧儚 URL
    """
    task = get_object_or_404(DetectionTask, id=task_id, user=request.user)

    include_img = request.query_params.get("include_image", "0") in ("1", "true", "True")
    result_list = []

    for dr in task.detection_results.select_related("image_upload"):
        item = {"result_id": dr.id, "image_id": dr.image_upload.id, "timestamp": dr.detection_time}
        if include_img:
            item["image_url"] = serialize_value(dr.image_upload.image, request)
        result_list.append(item)

    return Response({
        "task_id": task.id,
        "total_results": len(result_list),
        "results": result_list,
    })

# 澧炲姞涓や釜鎺ュ彛锛屽垎鍒繑鍥為€犲亣鐨勫浘鐗囷紝鍜屾甯哥殑鍥剧墖锛涘垽鍒柟寮忔槸detection_result.is_fake
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_fake_task_results(request, task_id):
    """
    ?include_image=1   鈥斺€?棰濆杩斿洖鍘熷鍥惧儚 URL
    """
    task = get_object_or_404(DetectionTask, id=task_id, user=request.user)

    include_img = request.query_params.get("include_image", "0") in ("1", "true", "True")
    result_list = []

    for dr in task.detection_results.select_related("image_upload"):
        if dr.is_fake:
            item = {"result_id": dr.id, "image_id": dr.image_upload.id, "timestamp": dr.detection_time}
            if include_img:
                item["image_url"] = serialize_value(dr.image_upload.image, request)
            result_list.append(item)

    return Response({
        "task_id": task.id,
        "total_results": len(result_list),
        "results": result_list,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_normal_task_results(request, task_id):
    """
    ?include_image=1   鈥斺€?棰濆杩斿洖鍘熷鍥惧儚 URL
    """
    task = get_object_or_404(DetectionTask, id=task_id, user=request.user)

    include_img = request.query_params.get("include_image", "0") in ("1", "true", "True")
    result_list = []

    for dr in task.detection_results.select_related("image_upload"):
        if not dr.is_fake:
            item = {"result_id": dr.id, "image_id": dr.image_upload.id, "timestamp": dr.detection_time}
            if include_img:
                item["image_url"] = serialize_value(dr.image_upload.image, request)
            result_list.append(item)

    return Response({
        "task_id": task.id,
        "total_results": len(result_list),
        "results": result_list,
    })


from rest_framework import serializers
from ..models import DetectionResult, SubDetectionResult
from django.db.models.fields.files import FieldFile

class SubDetectionResultSerializer(serializers.ModelSerializer):
    mask_image   = serializers.SerializerMethodField()
    mask_matrix  = serializers.SerializerMethodField()   # 鈫?鏂板

    class Meta:
        model  = SubDetectionResult
        fields = ["method", "probability", "mask_image", "mask_matrix"]

    # --- helpers ---------------------------------------------------------
    def get_mask_image(self, obj):
        req = self.context["request"]
        if isinstance(obj.mask_image, FieldFile) and obj.mask_image:
            return req.build_absolute_uri(obj.mask_image.url)
        return None

    def get_mask_matrix(self, obj):
        """
        鍙湁璋冪敤鏂瑰湪 context 閲屾樉寮忔爣璁?include_matrix=True 鏃舵墠杩斿洖
        """
        if self.context.get("include_matrix"):
            return obj.mask_matrix          # 宸茬粡鏄?list[list[float]]
        return None


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from ..models import DetectionResult
from ..utils.serializers_safe import serialize_value

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def detection_result_detail(request, result_id):
    dr = get_object_or_404(
        DetectionResult,
        id=result_id,
        # image_upload__file_management__user=request.user
    )

    # -------- 瑙ｆ瀽 fields & include_matrix ------------------------------
    raw_fields = request.query_params.get("fields")
    requested  = ({f.strip() for f in raw_fields.split(",")} if raw_fields
                  else {"overall", "llm", "llm_image", "ela_image", "exif", "timestamps",
                        "image", "sub_methods"})

    want_matrix = request.query_params.get("include_matrix", "0").lower() in ("1", "true", "yes")

    # -------- 鍩虹淇℃伅 ---------------------------------------------------
    data = {"result_id": dr.id}

    def add(name, value):
        if name in requested:
            data[name] = value

    add("overall", {
        "is_fake": dr.is_fake,
        "confidence_score": dr.confidence_score,
    })
    add("llm",          dr.llm_judgment)
    add("llm_image",    serialize_value(dr.llm_image, request))
    add("ela_image",    serialize_value(dr.ela_image, request))
    add("exif", {
        "photoshop_edited":  dr.exif_photoshop,
        "time_modified":     dr.exif_time_modified,
    })
    add("timestamps",   timezone.localtime(dr.detection_time))
    add("image",        serialize_value(dr.image_upload.image, request))

    # -------- 瀛愭柟娉?-----------------------------------------------------
    if "sub_methods" in requested:
        subs = dr.sub_results.all()
        ser  = SubDetectionResultSerializer(
            subs,
            many=True,
            context={"request": request, "include_matrix": want_matrix}
        )
        data["sub_methods"] = ser.data

    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def detection_result_by_image(request, image_id):
    # 閫氳繃image_id鑾峰彇瀵瑰簲鐨凞etectionResult
    dr = get_object_or_404(
        DetectionResult,
        image_upload__id=image_id,
        # image_upload__file_management__user=request.user
    )

    # -------- 瑙ｆ瀽 fields & include_matrix ------------------------------
    raw_fields = request.query_params.get("fields")
    requested = ({f.strip() for f in raw_fields.split(",")} if raw_fields
                 else {"overall", "llm", "ela_image", "exif", "timestamps",
                       "image", "sub_methods"})

    want_matrix = request.query_params.get("include_matrix", "0").lower() in ("1", "true", "yes")

    # -------- 鍩虹淇℃伅 ---------------------------------------------------
    data = {"result_id": dr.id}

    def add(name, value):
        if name in requested:
            data[name] = value

    add("overall", {
        "is_fake": dr.is_fake,
        "confidence_score": dr.confidence_score,
    })
    add("llm", dr.llm_judgment)
    add("ela_image", serialize_value(dr.ela_image, request))
    add("exif", {
        "photoshop_edited": dr.exif_photoshop,
        "time_modified": dr.exif_time_modified,
    })
    add("timestamps", dr.detection_time)
    add("image", serialize_value(dr.image_upload.image, request))

    # -------- 瀛愭柟娉?-----------------------------------------------------
    if "sub_methods" in requested:
        subs = dr.sub_results.all()
        ser = SubDetectionResultSerializer(
            subs,
            many=True,
            context={"request": request, "include_matrix": want_matrix}
        )
        data["sub_methods"] = ser.data

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_detection_task_status_normal(request, task_id):
    try:
        # 鑾峰彇浠诲姟鍜屽叧鑱旂殑妫€娴嬬粨鏋滐紝浠呭厑璁告湰浜鸿闂?
        detection_task = DetectionTask.objects.get(id=task_id, user=request.user)
        detection_results = DetectionResult.objects.filter(detection_task=detection_task)
        resource_files = detection_task.resource_files.all().order_by('id')

        result_summary = '检测进行中'
        if detection_task.status == 'failed':
            result_summary = detection_task.error_message or '检测失败'
        elif detection_task.status == 'completed':
            if detection_task.task_type == 'image':
                total = detection_results.count()
                fake = detection_results.filter(is_fake=True).count()
                result_summary = f'疑似造假 {fake}/{total}'
            elif detection_task.task_type == 'paper':
                result_summary = '论文检测已完成'
            elif detection_task.task_type == 'review':
                result_summary = 'Review 检测已完成'

        fake_resource_files = []
        normal_resource_files = []
        pending_resource_files = []
        split_note = None

        if detection_task.task_type == 'review':
            keywords = ['fake', 'aigc', '鐤戜技', '寮傚父', '鍙枒']
            for f in resource_files:
                file_item = {
                    "file_id": f.id,
                    "file_name": f.file_name,
                    "resource_type": f.resource_type,
                    "file_type": f.file_type,
                    "file_size": f.file_size,
                    "upload_time": timezone.localtime(f.upload_time),
                }
                if detection_task.status != 'completed':
                    pending_resource_files.append(file_item)
                elif any(k.lower() in (f.file_name or '').lower() for k in keywords):
                    fake_resource_files.append(file_item)
                else:
                    normal_resource_files.append(file_item)

            if detection_task.status == 'completed':
                split_note = 'Current fake/normal grouping for review tasks is placeholder logic based on filenames.'
        elif detection_task.task_type == 'paper':
            for f in resource_files:
                normal_resource_files.append({
                    "file_id": f.id,
                    "file_name": f.file_name,
                    "resource_type": f.resource_type,
                    "file_type": f.file_type,
                    "file_size": f.file_size,
                    "upload_time": timezone.localtime(f.upload_time),
                })
            if detection_task.status == 'completed':
                split_note = 'Paper detection currently does not expose fake/normal grouping.'

        # 鏀堕泦浠诲姟鐩稿叧鐨勫浘鍍忓拰鐘舵€佷俊鎭?
        task_status = {
            "task_id": detection_task.id,
            "task_name": detection_task.task_name,
            "task_type": detection_task.task_type,
            "status": detection_task.status,
            "upload_time": timezone.localtime(detection_task.upload_time),
            "completion_time": timezone.localtime(detection_task.completion_time) if detection_task.completion_time else None,
            "result_summary": result_summary,
            "error_message": detection_task.error_message,
            "is_running": detection_task.status in {"pending", "in_progress"},
            "progress": {
                "total_results": detection_results.count(),
                "completed_results": detection_results.filter(status="completed").count(),
                "pending_results": detection_results.filter(status="in_progress").count(),
                "failed_results": detection_results.filter(status="failed").count(),
            },
            "resource_files": [
                {
                    "file_id": f.id,
                    "file_name": f.file_name,
                    "resource_type": f.resource_type,
                    "file_type": f.file_type,
                    "file_size": f.file_size,
                    "upload_time": timezone.localtime(f.upload_time),
                }
                for f in resource_files
            ],
            "fake_resource_files": fake_resource_files,
            "normal_resource_files": normal_resource_files,
            "pending_resource_files": pending_resource_files,
            "resource_split_note": split_note,
            "detection_results": []
        }

        for result in detection_results:
            task_status["detection_results"].append({
                "image_id": result.image_upload.id,
                "status": result.status,
                "is_fake": result.is_fake,
                "confidence_score": result.confidence_score,
                "detection_time": timezone.localtime(result.detection_time),
            })

        return Response(task_status)

    except DetectionTask.DoesNotExist:
        return Response({"message": "Detection task not found or permission denied"}, status=404)

from rest_framework.pagination import PageNumberPagination

class CustomPagination(PageNumberPagination):
    page_size = 10  # 榛樿姣忛〉鏉℃暟
    page_size_query_param = 'page_size'  # 瀹㈡埛绔帶鍒舵瘡椤垫暟閲忕殑鍙傛暟鍚?
    max_page_size = 100  # 鍏佽瀹㈡埛绔缃殑鏈€澶ф瘡椤垫暟閲?

    def get_paginated_response(self, data):
        return Response({
            'page': self.page.number,
            'page_size': self.get_page_size(self.request),
            'total': self.page.paginator.count,
            'tasks': data
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_paper_detection_results(request, task_id):
    try:
        task = DetectionTask.objects.get(id=task_id, user=request.user)
        return Response({
            "task_id": task.id,
            "status": task.status,
            "results": task.text_detection_results or []
        })
    except DetectionTask.DoesNotExist:
        return Response({"message": "Detection task not found"}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_resource_task(request):
    user = request.user
    if not user.has_permission('submit'):
        return Response({'message': '璇ョ敤鎴锋病鏈夋彁浜ゆ娴嬩换鍔＄殑鏉冮檺'}, status=403)

    task_type = request.data.get('task_type', '')
    file_ids = request.data.get('file_ids', [])
    task_name = request.data.get('task_name', '').strip()

    if task_type not in {'paper', 'review'}:
        return Response({'message': 'task_type must be paper or review'}, status=400)

    if not isinstance(file_ids, list) or not file_ids:
        return Response({'message': 'file_ids is required and must be a non-empty list'}, status=400)

    if not task_name:
        if task_type == 'paper':
            task_name = f'璁烘枃妫€娴?{timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")}'
        else:
            task_name = f'Review妫€娴?{timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")}'

    files = FileManagement.objects.filter(id__in=file_ids, user=user)
    if files.count() != len(set(file_ids)):
        return Response({'message': 'Some files do not exist or do not belong to current user'}, status=404)

    file_list = list(files)
    resource_types = {f.resource_type for f in file_list}

    if task_type == 'paper':
        if resource_types != {'paper'}:
            return Response({'message': 'paper task only accepts paper resource files'}, status=400)
    else:
        if not ({'review_paper', 'review_file'} <= resource_types):
            return Response({'message': 'review task requires both review_paper and review_file'}, status=400)

        linked_ok = False
        review_papers = [f for f in file_list if f.resource_type == 'review_paper']
        review_files = [f for f in file_list if f.resource_type == 'review_file']
        for rv in review_files:
            if rv.linked_file and rv.linked_file.id in {rp.id for rp in review_papers}:
                linked_ok = True
                break
        if not linked_ok:
            return Response({'message': 'review_file is not correctly linked to review_paper'}, status=400)

    detection_task = DetectionTask.objects.create(
        organization=user.organization,
        user=user,
        task_type=task_type,
        task_name=task_name,
        status='pending',
    )
    detection_task.resource_files.add(*file_list)

    Log.objects.create(
        user=user,
        operation_type='detection',
        related_model='DetectionTask',
        related_id=detection_task.id,
    )

    if task_type == 'paper':
        from ..tasks import run_paper_detection
        api_key = request.data.get('api_key')
        run_paper_detection.delay(detection_task.id, api_key)

    return Response({
        'message': 'Resource task created successfully',
        'task_id': detection_task.id,
        'task_name': detection_task.task_name,
        'task_type': task_type,
        'file_ids': [f.id for f in file_list],
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_tasks(request):
    def parse_datetime_param(value):
        if not value:
            return None
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M',
            '%Y-%m-%d',
        ]
        for fmt in formats:
            try:
                parsed = datetime.strptime(value, fmt)
                if timezone.is_naive(parsed):
                    return timezone.make_aware(parsed, timezone.get_current_timezone())
                return parsed
            except ValueError:
                continue
        return 'invalid'

    # 鑾峰彇鍒嗛〉鍙傛暟
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 10))
    status = request.query_params.get('status', '').strip()
    task_type = request.query_params.get('task_type', '').strip()
    keyword = request.query_params.get('keyword', '').strip()
    start_time_raw = request.query_params.get('startTime', None)
    end_time_raw = request.query_params.get('endTime', None)

    start_time = parse_datetime_param(start_time_raw)
    end_time = parse_datetime_param(end_time_raw)

    if start_time == 'invalid':
        return Response({'error': 'Invalid startTime format'}, status=400)
    if end_time == 'invalid':
        return Response({'error': 'Invalid endTime format'}, status=400)
    if start_time and end_time and start_time >= end_time:
        return Response({'error': 'startTime must be earlier than endTime'}, status=400)

    # 鑾峰彇褰撳墠鐢ㄦ埛鐨勬墍鏈夋娴嬩换鍔″苟搴旂敤绛涢€夋潯浠讹紝榛樿灞曠ず鏈€杩戝崐骞?
    tasks = DetectionTask.objects.filter(user=request.user).order_by('-upload_time')

    if status:
        tasks = tasks.filter(status=status)

    if task_type:
        tasks = tasks.filter(task_type=task_type)

    if keyword:
        keyword_filter = Q(task_name__icontains=keyword)
        if keyword.isdigit():
            keyword_filter = keyword_filter | Q(id=int(keyword))
        tasks = tasks.filter(keyword_filter)

    if start_time:
        tasks = tasks.filter(upload_time__gte=start_time)
    if end_time:
        tasks = tasks.filter(upload_time__lte=end_time)
    if not start_time and not end_time:
        half_year_ago = timezone.now() - timedelta(days=183)
        tasks = tasks.filter(upload_time__gte=half_year_ago)

    paginator = Paginator(tasks, page_size)

    try:
        page_obj = paginator.page(page)
    except Exception:
        return Response({'error': 'Invalid page number'}, status=400)

    task_data = []
    for task in page_obj.object_list:
        result_summary = '检测进行中'
        if task.status == 'failed':
            result_summary = task.error_message or '检测失败'
        elif task.status == 'completed':
            if task.task_type == 'image':
                total = task.detection_results.count()
                fake = task.detection_results.filter(is_fake=True).count()
                result_summary = f'疑似造假 {fake}/{total}'
            elif task.task_type == 'paper':
                result_summary = '论文检测已完成'
            elif task.task_type == 'review':
                result_summary = 'Review 检测已完成'

        task_data.append({
            'task_id': task.id,
            'task_type': task.task_type,
            'task_name': task.task_name,
            'upload_time': timezone.localtime(task.upload_time).strftime('%Y-%m-%d %H:%M:%S'),
            'status': task.status,
            'result_summary': result_summary,
            'error_message': task.error_message,
            'completion_time': timezone.localtime(task.completion_time).strftime('%Y-%m-%d %H:%M:%S') if task.completion_time else None,
            'resource_file_ids': list(task.resource_files.values_list('id', flat=True))
        })

    return Response({
        'tasks': task_data,
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages,
        'total_tasks': paginator.count,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous()
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_tasks_depr(request):
    # 鑾峰彇褰撳墠鐢ㄦ埛鐨勬墍鏈夋娴嬩换鍔?
    detection_tasks = DetectionTask.objects.filter(user=request.user)
    task_list = []
    for task in detection_tasks:
        task_list.append({
            "task_id": task.id,
            "task_name": task.task_name,
            "status": task.status,
            "upload_time": timezone.localtime(task.upload_time),
            "completion_time": timezone.localtime(task.completion_time) if task.completion_time else None,
        })
    return Response(task_list)


from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated           # 濡傞渶閴存潈
from rest_framework.response import Response
from rest_framework import status

from ..models import (
    DetectionTask, ReviewRequest, ManualReview,
    DetectionResult, SubDetectionResult
)


def _delete_field_file(field) -> None:
    if isinstance(field, FieldFile) and field.name:
        field.delete(save=False)


def _cleanup_user_file_record(file_record: FileManagement) -> None:
    for image in list(file_record.image_uploads.all()):
        _delete_field_file(image.image)
        image.delete()

    stored_path = (file_record.stored_path or "").strip()
    if stored_path:
        abs_path = stored_path if os.path.isabs(stored_path) else os.path.join(settings.MEDIA_ROOT, stored_path)
        if os.path.isfile(abs_path):
            os.remove(abs_path)
        elif os.path.isdir(abs_path):
            shutil.rmtree(abs_path, ignore_errors=True)

    file_record.delete()


def _delete_detection_task_tree(task: DetectionTask) -> None:
    resource_files = list(task.resource_files.all())
    result_qs = DetectionResult.objects.filter(detection_task=task).select_related("image_upload")
    results = list(result_qs)

    for sub_result in SubDetectionResult.objects.filter(detection_result__in=result_qs):
        _delete_field_file(sub_result.mask_image)
        sub_result.delete()

    review_qs = ReviewRequest.objects.filter(detection_result__detection_task=task)
    ManualReview.objects.filter(review_request__in=review_qs).delete()
    review_qs.delete()

    for result in results:
        _delete_field_file(result.ela_image)
        _delete_field_file(result.llm_image)

    result_qs.delete()
    _delete_field_file(task.report_file)
    task.delete()

    for file_record in resource_files:
        if file_record.user_id != task.user_id:
            continue
        if file_record.detection_tasks.exists():
            continue
        _cleanup_user_file_record(file_record)


def _clear_all_detection_history_for_user(user) -> None:
    tasks = list(DetectionTask.objects.filter(user=user).order_by("id"))
    for task in tasks:
        _delete_detection_task_tree(task)

    for file_record in list(FileManagement.objects.filter(user=user)):
        _cleanup_user_file_record(file_record)

class DetectionTaskDeleteView(APIView):
    """
    鎸?task_id 鍒犻櫎妫€娴嬩换鍔″強鍏舵墍鏈夎鐢熸暟鎹?
    浠呭綋浠诲姟鐘舵€佷负 'completed' 鏃跺厑璁稿垹闄?
    """
    permission_classes = [IsAuthenticated]     # 鍙牴鎹渶瑕佹浛鎹紡鍒犲幓

    def delete(self, request, task_id, *args, **kwargs):
        try:
            task = DetectionTask.objects.get(pk=task_id, user=request.user)
        except DetectionTask.DoesNotExist:
            return Response(
                {"detail": "Task not found or permission denied."},
                status=status.HTTP_404_NOT_FOUND
            )

        if task.status == "in_progress":
            return Response(
                {"detail": "Task is still running and cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            _delete_detection_task_tree(task)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DetectionHistoryClearView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        with transaction.atomic():
            _clear_all_detection_history_for_user(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
