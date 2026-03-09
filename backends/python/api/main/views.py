import logging

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.clickjacking import xframe_options_exempt

from .services import (
    RobotExecutionContext,
    RobotHandlerNotFoundError,
    RobotResultService,
    dispatch_robot,
    get_robot_catalog,
    register_robots_in_bitrix24,
)
from .utils.decorators import auth_required, collect_request_data, log_errors
from .utils import AuthorizedRequest
from .models import ApplicationInstallation

from config import load_config

__all__ = [
    "root",
    "health",
    "public_health",
    "test",
    "get_enum",
    "get_list",
    "install",
    "get_token",
    "robots_catalog",
    "register_robots",
    "execute_robot",
    "debug_execute_robot",
]

config = load_config()
logger = logging.getLogger(__name__)


@xframe_options_exempt
@require_GET
@log_errors("root")
@auth_required
def root(request: AuthorizedRequest):
    return JsonResponse({"message": "Python Backend is running"})


@xframe_options_exempt
@require_GET
@log_errors("health")
@auth_required
def health(request: AuthorizedRequest):
    return JsonResponse({
        "status": "healthy",
        "backend": "python",
        "timestamp": timezone.now().timestamp(),
    })


@xframe_options_exempt
@require_GET
@log_errors("public_health")
def public_health(_request):
    return JsonResponse({
        "status": "healthy",
        "backend": "python",
        "service": "bitrix24-robots-api",
        "timestamp": timezone.now().timestamp(),
    })


@xframe_options_exempt
@require_GET
@log_errors("test")
def test(_request):
    return JsonResponse({
        "message": "Bitrix24 robots backend test endpoint is working",
        "backend": "python",
        "timestamp": timezone.now().timestamp(),
    })


@xframe_options_exempt
@require_GET
@log_errors("get_enum")
@auth_required
def get_enum(request: AuthorizedRequest):
    options = ["option 1", "option 2", "option 3"]
    return JsonResponse(options, safe=False)


@xframe_options_exempt
@require_GET
@log_errors("get_list")
@auth_required
def get_list(request: AuthorizedRequest):
    elements = ["element 1", "element 2", "element 3"]
    return JsonResponse(elements, safe=False)


@xframe_options_exempt
@csrf_exempt
@require_POST
@log_errors("install")
@auth_required
def install(request: AuthorizedRequest):
    bitrix24_account = request.bitrix24_account

    ApplicationInstallation.objects.update_or_create(
        bitrix_24_account=bitrix24_account,
        defaults={
            "status": bitrix24_account.status,
            "portal_license_family": "",
            "application_token": bitrix24_account.application_token,
        },
    )

    return JsonResponse({"message": "Installation successful"})


@xframe_options_exempt
@csrf_exempt
@require_POST
@log_errors("get_token")
@auth_required
def get_token(request: AuthorizedRequest):
    return JsonResponse({"token": request.bitrix24_account.create_jwt_token()})


@xframe_options_exempt
@require_GET
@log_errors("robots_catalog")
def robots_catalog(_request):
    return JsonResponse({
        "robots": get_robot_catalog(config.app_base_url),
    })


@xframe_options_exempt
@csrf_exempt
@require_POST
@log_errors("register_robots")
@auth_required
def register_robots(request: AuthorizedRequest):
    auth_user_id = int(request.data.get("AUTH_USER_ID", request.bitrix24_account.b24_user_id))
    registered_robots = register_robots_in_bitrix24(
        bitrix24_account=request.bitrix24_account,
        app_base_url=config.app_base_url,
        auth_user_id=auth_user_id,
    )

    return JsonResponse({
        "status": "ok",
        "registered_robots": registered_robots,
    })


@xframe_options_exempt
@csrf_exempt
@require_POST
@log_errors("execute_robot")
@auth_required
def execute_robot(request: AuthorizedRequest, robot_code: str):
    try:
        context = RobotExecutionContext(
            robot_code=robot_code,
            payload=request.data,
            bitrix24_account=request.bitrix24_account,
            is_debug=False,
        )
        handler_result = dispatch_robot(context)
        response_payload = RobotResultService(request.bitrix24_account).finalize(context, handler_result)
    except RobotHandlerNotFoundError as error:
        logger.warning("Robot handler not found for code '%s'", robot_code)
        return JsonResponse({"error": str(error)}, status=404)

    return JsonResponse(response_payload)


@xframe_options_exempt
@csrf_exempt
@require_POST
@log_errors("debug_execute_robot")
@collect_request_data
def debug_execute_robot(request, robot_code: str):
    try:
        context = RobotExecutionContext(
            robot_code=robot_code,
            payload=request.data,
            bitrix24_account=None,
            is_debug=True,
        )
        handler_result = dispatch_robot(context)
        response_payload = RobotResultService().finalize(context, handler_result)
    except RobotHandlerNotFoundError as error:
        logger.warning("Debug robot handler not found for code '%s'", robot_code)
        return JsonResponse({"error": str(error)}, status=404)

    response_payload["debug_endpoint"] = True
    return JsonResponse(response_payload)
