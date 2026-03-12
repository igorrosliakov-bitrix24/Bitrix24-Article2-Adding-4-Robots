import os

from ..workers.tasks import execute_robot_task


class RobotQueueService:
    @staticmethod
    def is_enabled() -> bool:
        return os.getenv("ENABLE_RABBITMQ", "0") == "1"

    @staticmethod
    def enqueue(robot_code: str, payload: dict, is_debug: bool = False) -> str:
        # Stage 7 queue entrypoint: the HTTP layer pushes the robot job here,
        # then Celery/RabbitMQ forwards it to the worker process.
        task = execute_robot_task.delay(robot_code, payload, is_debug)
        return task.id
