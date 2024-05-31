from django.urls import path

from apps.message.webSockets.message_client import MessageClient
from apps.node_manager.websocket.node_client import node_client
from apps.node_manager.websocket.node_control import node_control

websocket_urlpatterns = [
    # 节点客户端
    path(r"ws/node/node_client", node_client.as_asgi()),
    # 节点控制器
    path(r"ws/node/node_control/<str:node_uuid>/", node_control.as_asgi()),
    # 消息通知
    path(r"ws/message", MessageClient.as_asgi())
]
