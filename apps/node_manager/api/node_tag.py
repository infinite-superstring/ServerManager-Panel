from django.views.decorators.http import require_POST

from util.Request import RequestLoadJson
from util.Response import ResponseJson
from util.logger import Log
from apps.node_manager.utils.tagUtil import get_tag_by_name


def add_tag(req):
    """添加tag"""


def del_tag(req):
    """删除tag"""


@require_POST
def search_tag(req):
    """搜索tag"""
    try:
        req_json = RequestLoadJson(req)
    except Exception as e:
        Log.error(e)
        return ResponseJson({"status": -1, "msg": "JSON解析失败"}, 400)
    else:
        tag = req_json.get('tag')
        if tag:
            return ResponseJson({
                "status": 1,
                "msg": "OK",
                "data": {
                    "tags": get_tag_by_name(tag)
                }
            })
        else:
            return ResponseJson({
                "status": -1,
                "msg": "参数不完整"
            })

