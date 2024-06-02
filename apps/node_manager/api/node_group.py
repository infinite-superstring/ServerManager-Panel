from apps.node_manager.models import Node_Group
from apps.node_manager.utils.groupUtil import create_message_recipient_rules
from apps.node_manager.utils.nodeUtil import node_uuid_exists, get_node_by_uuid, node_set_group
from apps.user_manager.util.userUtils import uid_exists, get_user_by_id
from util.Request import RequestLoadJson
from util.Response import ResponseJson
from util.logger import Log
from util.pageUtils import get_page_content, get_max_page


def get_group_list(req):
    if req.method != 'POST':
        return ResponseJson({"status": -1, "msg": "请求方式不正确"}, 405)
    try:
        req_json = RequestLoadJson(req)
    except Exception as e:
        Log.error(e)
        return ResponseJson({"status": -1, "msg": "JSON解析失败"}, 400)
    PageContent: list = []
    page = req_json.get("page", 1)
    pageSize = req_json.get("pageSize", 20)
    search = req_json.get("search", "")
    result = Node_Group.objects.filter(name__icontains=search)
    pageQuery = get_page_content(result, page if page > 0 else 1, pageSize)
    if pageQuery:
        for item in pageQuery:
            PageContent.append({
                "group_id": item.get("id"),
                "group_name": item.get("name"),
            })
    return ResponseJson({
        "status": 1,
        "data": {
            "maxPage": get_max_page(result.all().count(), 20),
            "currentPage": page,
            "PageContent": PageContent
        }
    })

def create_group(req):
    """创建组"""
    if req.method != 'POST':
        return ResponseJson({"status": -1, "msg": "请求方式不正确"}, 405)
    try:
        req_json = RequestLoadJson(req)
    except Exception as e:
        Log.error(e)
        return ResponseJson({"status": -1, "msg": "JSON解析失败"}, 400)
    # 组名
    group_name: str = req_json.get('group_name')
    # 组介绍
    group_desc: str = req_json.get('group_desc')
    # 组负责人
    group_leader: int = req_json.get('group_leader')
    # 组节点列表
    group_nodes: list = req_json.get('group_nodes')
    # 组消息发送规则
    time_slot_recipient: list = req_json.get('time_slot_recipient')
    if not (group_name and group_desc and group_leader):
        return ResponseJson({'status': -1, 'msg': '参数不完整'})
    if Node_Group.objects.filter(name=group_name).exists():
        return ResponseJson({"status": 0, "msg": "节点组已存在"})
    if not uid_exists(group_leader):
        return ResponseJson({'status': 0, 'msg': '节点组负责人不存在'})
    group = Node_Group.objects.create(
        name=group_name,
        description=group_desc,
        leader=get_user_by_id(group_leader)
    )
    for node in group_nodes:
        if not node_uuid_exists(node):
            Log.warning(f"节点{node}不存在")
            continue
        node_set_group(node, group.id)
    rules = create_message_recipient_rules(time_slot_recipient)
    for rule in rules:
        group.time_slot_recipient.add(rule)
    return ResponseJson({'status': 1, 'msg': '节点组创建成功'})

def del_group(req):
    """删除组"""


def edit_group(req):
    """编辑组"""
