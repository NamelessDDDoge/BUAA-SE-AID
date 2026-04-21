from ...local_detection import execute_detection_task


def run_image_detection_task(*, detection_task, image_uploads):
    return execute_detection_task(detection_task, image_uploads)
