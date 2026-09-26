"""设施台账接口：维护设施，覆盖组合筛选、分页排序、明细与状态流转。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.facility import SORT_FIELDS, STATUS_ORDER, FacilityService

router = APIRouter(prefix="/api/facility", tags=["设施台账"])

service = FacilityService()

LIST_FIELDS = ["设施编号", "设施名称", "设施类型", "所在路段", "管养单位", "建设年代", "设计等级", "设施状态"]
STATUSES = list(STATUS_ORDER)


@dataclass
class ListParams:
    """列表与导出共用的筛选/排序口径，避免两处实现漂移。"""

    code: str | None = None
    name: str | None = None
    unit: str | None = None
    facility_type: str | None = None
    status: str | None = None
    sort_by: str = "设施编号"
    order: str = "asc"
    page: int = 1
    size: int = 10


def list_params(
    code: str | None = Query(default=None, description="按设施编号模糊检索"),
    keyword: str | None = Query(default=None, description="设施编号的兼容别名"),
    name: str | None = Query(default=None, description="按设施名称模糊检索"),
    unit: str | None = Query(default=None, description="按管养单位模糊检索"),
    facility_type: str | None = Query(default=None, alias="type", description="按设施类型精确筛选"),
    status: str | None = Query(default=None, description="正常运行、限制通行、封闭维修、已废弃"),
    sort_by: str = Query(default="设施编号", description="排序字段"),
    order: str = Query(default="asc", description="asc 正序 / desc 倒序"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1),
) -> ListParams:
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    if status is not None and status not in STATUS_ORDER:
        raise HTTPException(status_code=400, detail=f"状态「{status}」不在可选范围内")
    if sort_by not in SORT_FIELDS:
        raise HTTPException(status_code=400, detail=f"暂不支持按「{sort_by}」排序")
    if order not in ("asc", "desc"):
        raise HTTPException(status_code=400, detail="排序方向只支持 asc 或 desc")
    return ListParams(
        code=(code or keyword or None),
        name=name,
        unit=unit,
        facility_type=facility_type,
        status=status,
        sort_by=sort_by,
        order=order,
        page=page,
        size=size,
    )


@router.get("", response_model=PageResult[dict])
def list_entries(params: ListParams = Depends(list_params)) -> PageResult[dict]:
    """按设施编号、名称、管养单位、类型、状态组合筛选并分页；没有命中时返回空页，不报错。"""
    items, total = service.list_entries(
        code=params.code,
        name=params.name,
        unit=params.unit,
        facility_type=params.facility_type,
        status=params.status,
        sort_by=params.sort_by,
        order=params.order,
        page=params.page,
        size=params.size,
    )
    return PageResult(items=items, total=total, page=params.page, size=params.size)


@router.get("/meta")
def list_meta() -> dict[str, Any]:
    """下拉候选（设施类型、管养单位、状态）与状态统计。"""
    return service.meta()


@router.get("/export")
def export_entries(params: ListParams = Depends(list_params)) -> dict[str, Any]:
    """导出设施台账清单：返回当前筛选条件下的全量数据，导出不随列表翻页截断。"""
    items, total = service.list_entries(
        code=params.code,
        name=params.name,
        unit=params.unit,
        facility_type=params.facility_type,
        status=params.status,
        sort_by=params.sort_by,
        order=params.order,
        page=1,
        size=10000,
    )
    return {"module": "facility", "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条设施明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"设施 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条设施，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="设施已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条设施执行限制通行、封闭维修、恢复通行；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
