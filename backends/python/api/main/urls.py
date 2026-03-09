from django.urls import path
from .views import *

urlpatterns = [
    path('api', root, name='root'),
    path('api/health', health, name='health'),
    path('api/public/health', public_health, name='public_health'),
    path('api/test', test, name='test'),
    path('api/robots/catalog', robots_catalog, name='robots_catalog'),
    path('api/robots/register', register_robots, name='register_robots'),
    path('api/robots/execute/<str:robot_code>', execute_robot, name='execute_robot'),
    path('api/robots/debug/execute/<str:robot_code>', debug_execute_robot, name='debug_execute_robot'),
    path('api/enum', get_enum, name='enum'),
    path('api/list', get_list, name='list'),
    path('api/install', install, name='install'),
    path('api/getToken', get_token, name='get_token'),
]
