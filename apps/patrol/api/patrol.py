from django.http import HttpRequest

from apps.permission_manager.util.api_permission import api_permission
from apps.user_manager.util.userUtils import get_user_by_id
from util.Request import RequestLoadJson
from util.Response import ResponseJson
from util.logger import Log
from apps.patrol.models import Patrol
from util.pageUtils import get_page_content, get_max_page


@api_permission("viewPatrol")
def addARecord(req: HttpRequest):
    if req.method != "POST":
        return ResponseJson({"status": -1, "msg": "请求方式不正确"}, 405)
    try:
        data = RequestLoadJson(req)
    except Exception as e:
        Log.error(e)
        return ResponseJson({"status": -1, "msg": f"JSON解析失败:{e}"}, 400)
    else:
        user_id = req.session.get("userID")
        content = data.get("content")
        status = data.get("status")
        title = data.get("title")
        if content is None or status is None or title is None:
            return ResponseJson({"status": -1, "msg": "参数错误"}, 400)
        Patrol.objects.create(user_id=user_id, content=content, status=status, title=title)
    return ResponseJson({"status": 1, "msg": "添加成功"})


@api_permission("viewPatrol")
def getList(req: HttpRequest):
    if req.method != "POST":
        return ResponseJson({"status": -1, "msg": "请求方式不正确"}, 405)
    try:
        data = RequestLoadJson(req)
    except Exception as e:
        Log.error(e)
        return ResponseJson({"status": -1, "msg": f"JSON解析失败:{e}"}, 400)
    else:
        PageContent = []
        page = data.get("page", 1)
        pageSize = data.get("pageSize", 20)
        result = Patrol.objects.filter()
        pageQuery = get_page_content(result, page if page > 0 else 1, pageSize)
        if pageQuery:
            for item in pageQuery:
                PageContent.append({
                    "id": item.get("id"),
                    "user": get_user_by_id(item.get("user_id")).userName if item.get("user_id") else None,
                    "content": item.get("content"),
                    "status": item.get("status"),
                    "title": item.get("title"),
                    "time": item.get("time"),
                })
        return ResponseJson({
            "status": 1,
            "data": {
                "maxPage": get_max_page(result.count(), 20),
                "currentPage": page,
                "PageContent": PageContent
            }
        })


@api_permission("editPatrol")
def updateRecord(req: HttpRequest):
    if req.method != "PUT":
        return ResponseJson({"status": -1, "msg": "请求方式不正确"}, 405)
    try:
        data = RequestLoadJson(req)
    except Exception as e:
        Log.error(e)
        return ResponseJson({"status": -1, "msg": f"JSON解析失败:{e}"}, 400)
    else:
        id = data.get("id")
        content = data.get("content")
        status = data.get("status")
        title = data.get("title")
        if id is None or content is None or status is None or title is None:
            return ResponseJson({"status": -1, "msg": "参数错误"}, 400)
        Patrol.objects.filter(id=id).update(content=content, status=status, title=title)
    return ResponseJson({"status": 1, "msg": "更新成功"})


@api_permission("editPatrol")
def deleteRecord(req: HttpRequest):
    if req.method != "DELETE":
        return ResponseJson({"status": -1, "msg": "请求方式不正确"}, 405)

    else:
        id = req.GET.get("id")
        if id is None:
            return ResponseJson({"status": -1, "msg": "参数错误"}, 400)
        if not Patrol.objects.filter(id=id).exists():
            return ResponseJson({"status": -1, "msg": "记录不存在"}, 400)
        if not req.session.get("userID") == Patrol.objects.get(id=id).user_id:
            return ResponseJson({"status": -1, "msg": "权限不足"})
        Patrol.objects.filter(id=id).delete()
        return ResponseJson({"status": 1, "msg": "删除成功"})
