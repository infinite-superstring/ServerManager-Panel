import os.path
import uuid
from datetime import datetime

from asgiref.sync import async_to_sync
from django.http import HttpRequest

from apps.group_task.models import GroupTask
from apps.group_task.utils import group_task_util
from apps.node_manager.models import Node_Group, Node
from util import result, pageUtils
from util.Request import RequestLoadJson
from django.apps import apps


def create_group_task(req: HttpRequest):
    """
    创建集群任务
    """
    if req.method != 'POST':
        return result.api_error('请求方式错误', http_code=405)
    try:
        data = RequestLoadJson(req)
    except:
        return result.api_error('请求数据错误', http_code=400)
    taskName: str = data.get('taskName', '')
    group: int = data.get('group', 0)
    execCount: int = data.get('execCount', )
    execType: str = data.get('execType', '')
    command: str = data.get('command', '')
    execPath: str = data.get('execPath', '')
    enable: bool = data.get('enable', False)
    if GroupTask.objects.filter(name=taskName).exists():
        return result.error('任务名称已存在')
    if (not taskName or
            not group or
            not execType or
            not command):
        return result.error('请将参数填写完整')
    if execPath and not os.path.isabs(execPath):
        return result.error('执行路径格式错误')
    g_task: GroupTask = GroupTask()
    g_task.name = taskName
    g_task.node_group_id = group
    g_task.exec_type = execType
    g_task.command = command
    g_task.enable = enable
    g_task.exec_path = execPath if execPath else None
    if execCount:
        g_task.exec_count = execCount
    if execType == 'date-time':
        execTime: str = data.get('execTime', '')
        if not execTime:
            return result.error('请选择执行时间')
        g_task.that_time = execTime
    if execType == 'interval':
        execInterval: str = data.get('execInterval', '')
        if not execInterval:
            return result.error('请选择执行间隔')
        g_task.interval = execInterval
    g_task.save()
    if execType == 'cycle':
        execCycle: dict = data.get('execCycle', {})
        cycle = group_task_util.createCycle(execCycle, g_task)
        if cycle.group_task.name != g_task.name:
            return result.api_error('周期设置错误')
        cycle.save()
        group_task_util.handle_change_task(t='add', task=g_task)
    return result.success(msg='添加成功')


def get_list(req: HttpRequest):
    """
    获取集群任务列表
    """
    if req.method != 'GET':
        return result.api_error('请求方式错误', http_code=405)
    params = dict(req.GET)
    page = params.get('page', 1)
    page_size = params.get('pageSize', 20)
    search = params.get('search', '')
    query_results = GroupTask.objects.filter(
        name__contains=search,
        node_group__name__contains=search,
        node_group__description__contains=search,
    )
    page_result: dict = pageUtils.get_page_content(query_results, page, page_size)
    max_page = pageUtils.get_max_page(query_results.count(), page_size)
    r_list = []
    for g in page_result:
        node_group = Node_Group.objects.get(id=g.get('node_group_id'))
        cycle = {}
        if g.get('exec_type') == 'cycle':
            cycle = async_to_sync(group_task_util.getCycle)((g.get('uuid')))
        r_list.append({
            'uuid': g.get('uuid'),
            'name': g.get('name'),
            'node_group_name': node_group.name,
            'exec_type': g.get('exec_type'),
            'exec_count': g.get('exec_count'),
            'interval': g.get('interval'),
            'that_time': g.get('that_time'),
            'enable': g.get('enable'),
            'exec_path': g.get('exec_path'),
            'cycle': cycle,
        })
    response = {
        'list': r_list,
        'maxPage': max_page,
        'total': query_results.count()
    }
    return result.success(data=response)


def change_enable(req: HttpRequest):
    """
    更改任务状态
    """
    if req.method != 'PUT':
        return result.api_error('请求方式错误', http_code=405)
    try:
        data = RequestLoadJson(req)
    except:
        return result.api_error('请求数据错误', http_code=400)
    uuids: str = data.get('uuid', '')
    if not uuids:
        return result.error('请选择任务')
    g: GroupTask = GroupTask.objects.filter(uuid=uuids).first()
    if not g:
        return result.error('任务不存在')
    g.enable = not g.enable
    g.save()
    group_task_util.handle_change_task(t='reload', task=g)
    return result.success(msg=f'任务{g.name}已{"启用" if g.enable else "禁用"}')


def delete_by_uuid(req: HttpRequest):
    """
    根据 uuid 删除任务
    """
    if req.method != 'DELETE':
        return result.api_error('请求方式错误', http_code=405)
    uuids: str = req.GET.get('uuid', '')
    if not uuids:
        return result.error('请选择任务')
    group: GroupTask = GroupTask.objects.filter(uuid=uuids).first()
    if not group:
        return result.error('任务不存在')
    node_group = group.node_group
    group.delete()
    group_task_util.handle_change_task(t='remove', group=node_group)
    return result.success(msg='删除成功')


async def by_node_uuid_get_task(uuids: str):
    """
    根据 节点 ID 获取 任务 列表

    执行类型:
        指定时间 -> 'date-time'
        周期 -> 'cycle'
        间隔 -> 'interval'
    """
    return await group_task_util.by_uuid_get_task(uuids=uuids)


async def handle_group_task(task_uuid, node_uuid, result_text, result_code):
    """
    用于处理 集群 任务 返回结果

    """
    save_base_dir: str = apps.get_app_config('node_manager').group_task_result_save_dir
    result_uuid = str(uuid.uuid4())
    task_dir = os.path.join(
        save_base_dir,
        task_uuid,
        node_uuid,
        result_uuid
    )
    with open(task_dir) as f:
        pass
