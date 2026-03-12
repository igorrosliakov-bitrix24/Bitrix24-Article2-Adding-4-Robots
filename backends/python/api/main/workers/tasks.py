from celery_app import celery_app

from ..services.robot_execution_service import RobotExecutionService


@celery_app.task(name="bitrix24.execute_robot")
def execute_robot_task(robot_code: str, payload: dict, is_debug: bool = False) -> dict:
    # Stage 7 worker entrypoint: the worker executes the same shared robot pipeline
    # that the synchronous HTTP flow uses.
    return RobotExecutionService.execute(robot_code=robot_code, payload=payload, is_debug=is_debug)
