import os.path
from datetime import datetime
from typing import Callable

from asgiref.sync import async_to_sync
from django.apps import apps
from django.db.models import QuerySet
from django.http import HttpRequest
from django.views.decorators.http import require_http_methods, require_POST, require_GET

from apps.audit.util.auditTools import write_audit
from apps.group.group_task.models import GroupTask, Group_Task_Audit
from apps.group.group_task.utils import group_task_util
from apps.group.group_task.utils.group_task_util import filer_page_result
from apps.node_manager.models import Node
from apps.group.manager.models import Node_Group
from apps.group.manager.utils.groupUtil import get_node_group_by_id
from apps.permission_manager.util.api_permission import api_permission
from apps.setting.entity.Config import config
from apps.permission_manager.util.permission import groupPermission
from apps.user_manager.util.userUtils import get_user_by_id
from util import result, pageUtils, file_util
from util.Request import RequestLoadJson
from util.file_util import SizeType

# 获取配置
config: Callable[[], config] = apps.get_app_config('setting').get_config


# @require_POST
@require_http_methods(['PUT', 'POST'])
@api_permission('clusterTask')
def create_group_task(req: HttpRequest):
    """
    创建集群任务
    """
    try:
        data = RequestLoadJson(req)
    except:
        return result.api_error('请求数据错误', http_code=400)
    taskName: str = data.get('taskName', '')
    group: int = data.get('group', 0)
    execCount: int | None = data.get('execCount', None)
    execType: str = data.get('execType', '')
    command: str = data.get('command', '')
    execPath: str = data.get('execPath', '')
    enable: bool = data.get('enable', False)
    if req.method != 'PUT' and GroupTask.objects.filter(name=taskName).exists():
        return result.error('任务名称已存在')
    if (not taskName or
            not group or
            not execType or
            not command):
        return result.error('请将参数填写完整')
    command_list = config().terminal_audit.disable_command_list
    gp = groupPermission(get_user_by_id(req.session.get("userID")).permission)
    if not gp.is_superuser() and not group_task_util.command_legal(command=command,
                                                                   command_list=command_list.split('\n')):
        return result.error('禁用命令不可执行')
    if execPath and not os.path.isabs(execPath):
        return result.error('执行路径格式错误')
    if req.method == 'PUT':
        try:
            g_task: GroupTask = GroupTask.objects.get(uuid=data.get('uuid', ''))
        except GroupTask.DoesNotExist:
            return result.error('任务不存在')
    else:
        g_task: GroupTask = GroupTask()
    g_task.name = taskName
    g_task.node_group_id = group
    g_task.exec_type = execType
    g_task.command = command
    g_task.enable = enable
    if execCount:
        if int(execCount) < 1:
            return result.error('执行次数不能小于1')
        g_task.exec_count = int(execCount)
    if execType == 'date-time':
        execTime: str = data.get('execTime', '')
        if not execTime:
            return result.error('请选择执行时间')
        try:
            date_time_exec_time = datetime.strptime(execTime, '%Y-%m-%dT%H:%M')
        except ValueError:
            date_time_exec_time = datetime.strptime(execTime, '%Y-%m-%d %H:%M:%S')
        if date_time_exec_time.timestamp() < datetime.now().timestamp():
            return result.error('执行时间不能小于当前时间')
        g_task.that_time = date_time_exec_time
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
    if req.method == 'PUT':
        group_task_util.handle_change_task(t='reload', task=g_task, group=g_task.node_group)
    else:
        group_task_util.handle_change_task(t='add', task=g_task)
    write_audit(req.session['userID'], "新增集群任务", "集群任务",
                f"任务名: {taskName} 执行集群：{get_node_group_by_id(group).name} 执行方式：{execType} 执行目录：{execPath if execPath else 'Default'} shell：{command}")
    return result.success(msg='操作完成')


@require_GET
def get_list(req: HttpRequest):
    """
    获取集群任务列表
    """
    page = req.GET.get('page', 1)
    page_size = req.GET.get('pageSize', 20)
    search = req.GET.get('search', "")
    enable: int | None = req.GET.get('enable', None)
    exec_type: str | None = req.GET.get('execType', None)
    node_group: int | None = req.GET.get('node_group', None)
    query_results = GroupTask.objects.filter(name__contains=search)
    query_results = filer_page_result(r_l=query_results,
                                      enable=int(enable) if enable is not None else None,
                                      exec_type=exec_type,
                                      node_group=node_group)
    page_result = pageUtils.get_page_content(query_results, int(page), int(page_size))
    max_page = pageUtils.get_max_page(int(query_results.count()), int(page_size))
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
            'command': g.get('command'),
            'cycle': cycle,
        })
    response = {
        'list': r_list,
        'maxPage': max_page,
        'total': query_results.count()
    }
    return result.success(data=response)


@api_permission('clusterTask')
def get_task_name(req: HttpRequest):
    """
    获取所有任务名称
    """
    all_tasks = GroupTask.objects.all()
    return result.success(data=[
        {
            'id': t.uuid,
            'title': t.name,
            'sign': 'task',
            'children': []
        }
        for t in all_tasks])


@require_GET
@api_permission('clusterTask')
def by_task_uuid_get_node(req: HttpRequest):
    """
    根据任务UUID获取节点
    """
    task_uuid = req.GET.get('uuid', '')
    node_group: Node_Group = GroupTask.objects.get(uuid=task_uuid).node_group
    nodes = Node.objects.filter(group=node_group)
    return result.success(data=[
        {
            'id': n.uuid,
            'task_uuid': task_uuid,
            'title': n.name,
            'sign': 'node',
            'children': []
        }
        for n in nodes])


@require_GET
@api_permission('clusterTask')
def by_node_uuid_get_result(req: HttpRequest):
    node_uuid = req.GET.get('uuid', '')
    task_uuid = req.GET.get('task_uuid', '')
    show_count = req.GET.get('show_count', 30)
    group_task_audit = Group_Task_Audit.objects.filter(
        node__uuid=node_uuid,
        group_task__uuid=task_uuid,
        end_time__isnull=False

    ).order_by('-statr_time')[:int(show_count)]
    return result.success(data=[
        {
            'id': t.uuid,
            'title': t.statr_time,
            'value': {
                'uuid': t.uuid,
                'node_uuid': node_uuid,
                'task_uuid': task_uuid
            }
        }
        for t in group_task_audit])


@require_GET
@api_permission('clusterTask')
def get_result_detail(req: HttpRequest):
    uuid = req.GET.get('uuid', '')
    node_uuid = req.GET.get('node_uuid', '')
    task_uuid = req.GET.get('task_uuid', '')
    if not group_task_util.is_uuid(uuid) or \
            not group_task_util.is_uuid(node_uuid) or \
            not group_task_util.is_uuid(task_uuid):
        return result.error('参数错误')
    save_dir = apps.get_app_config('node_manager').group_task_result_save_dir
    file_path = os.path.join(save_dir, task_uuid, node_uuid, uuid)
    # 文件大小大于 3 M 则提示下载
    if file_util.file_to_size(file_path=str(file_path), size_type=SizeType.MB) > 3:
        return result.error(msg='文件过大，请下载查看')
    c = file_util.file_encode(file_path=str(file_path)) or 'utf-8'
    commandLine = file_util.read_text_file(file_path=str(file_path), encoding=c)
    if commandLine:
        return result.success(commandLine)
    return result.error(msg='文件读取失败')


@require_http_methods("PUT")
@api_permission('clusterTask')
def change_enable(req: HttpRequest):
    """
    更改任务状态
    """
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
    if g.enable:
        if g.exec_count and int(g.exec_count) <= 0:
            return result.error('任务次数已执行完成')
        group_task_util.handle_change_task(t='add', group=g.node_group, task=g)
    else:
        group_task_util.handle_change_task(t='remove', group=g.node_group, task_uuid=g.uuid, task=g)
    write_audit(req.session['userID'], f"{'启用' if g.enable else '禁用'}集群任务", "集群任务", f"task：{g.uuid}")
    return result.success(msg=f'任务{g.name}已{"启用" if g.enable else "禁用"}')


@require_http_methods("DELETE")
@api_permission('clusterTask')
def delete_by_uuid(req: HttpRequest):
    """
    根据 uuid 删除任务
    """
    uuids: str = req.GET.get('uuid', '')
    if not uuids:
        return result.error('请选择任务')
    group: GroupTask = GroupTask.objects.filter(uuid=uuids).first()
    if not group:
        return result.error('任务不存在')
    node_group = group.node_group
    task_uuid = group.uuid
    group.delete()
    group_task_util.handle_change_task(t='remove', group=node_group, task_uuid=task_uuid)
    write_audit(req.session['userID'], f"删除集群任务", "集群任务", f"task：{uuids}")
    return result.success(msg='删除成功')


async def by_node_uuid_get_task(node_uuid: str, group: Node_Group = None):
    """
    根据 节点 ID 获取 任务 列表

    执行类型:
        指定时间 -> 'date-time'
        周期 -> 'cycle'
        间隔 -> 'interval'
    """
    group_tasks = []
    group_task: QuerySet[GroupTask] = QuerySet[GroupTask]()
    if node_uuid:
        groups: QuerySet[Node_Group] = Node_Group.objects.filter(node__uuid=node_uuid)
        if not await groups.aexists():
            return group_tasks
        group = await groups.afirst()
        group_task = GroupTask.objects.filter(node_group=group)
    if group:
        group_task = GroupTask.objects.filter(node_group=group)
    async for task in group_task:
        # 检查任务是否不应该推送
        if group_task_util.task_should_not_push(task):
            continue
        group_tasks.append(await group_task_util.get_the_task_of_node(task=task))
    return group_tasks


@require_GET
@api_permission('clusterTask')
def get_task_detailed(req: HttpRequest):
    """
    获取任务详情
    """
    uuid = req.GET.get('uuid', '')
    task: GroupTask = GroupTask.objects.filter(uuid=uuid).first()
    if not task:
        return result.error('任务不存在')
    data = async_to_sync(group_task_util.get_the_task_of_node)(task=task)
    return result.success(data=data)


@require_GET
@api_permission('clusterTask')
def get_task_by_uuid(req: HttpRequest):
    """
    根据 uuid 获取任务
    """
    task: GroupTask = GroupTask.objects.filter(uuid=req.GET.get('uuid', '')).first()
    if not task:
        return result.error('任务不存在')
    exec_cycle = {}
    if task.exec_type == 'cycle':
        exec_cycle = async_to_sync(group_task_util.getCycle)(task.uuid)
    r_data = {
        'taskName': task.name,
        'group': task.node_group.id,
        'execCount': task.exec_count,
        'execType': task.exec_type,
        'execTime': task.that_time,
        'execInterval': task.interval,
        'command': task.command,
        'execPath': task.exec_path,
        'enable': task.enable,
        'execCycle': exec_cycle
    }
    return result.success(r_data)


@require_POST
@api_permission('clusterTask')
def command_legal(req: HttpRequest):
    """
    命令是否合法
    """
    disable_command_list: [list[str]] = config().terminal_audit.disable_command_list.split('\n')
    warn_command_list: [list[str]] = config().terminal_audit.warn_command_list.split('\n')
    try:
        data = RequestLoadJson(req)
    except Exception as e:
        return result.api_error('请求数据错误', http_code=400)
    command = data.get('command', '')

    gp = groupPermission(get_user_by_id(req.session.get("userID")).permission)
    if gp.is_superuser():
        return result.success(data=True)

    if not command:
        return result.error('请输入命令')

    if not group_task_util.command_legal(command, warn_command_list):
        # 命令在警告列表中
        return result.success(data=False, msg='命令在警告列表中')
    if not group_task_util.command_legal(command, disable_command_list):
        # 命令在禁用列表中
        return result.error('命令已禁用')
    return result.success(data=True)
