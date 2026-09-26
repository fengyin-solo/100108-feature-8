"""设施台账接口：维护设施，覆盖限制通行、封闭维修、恢复通行等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.facility import SORTABLE_FIELDS, STATUS_ORDER, FacilityService

router = APIRouter(prefix="/api/facility", tags=["设施台账"])

service = FacilityService()


def _parse_filters(
    code: str | None,
    name: str | None,
    unit: str | None,
    section: str | None,
    facility_type: str | None,
    status: str | None,
    sort: str,
    order: str,
) -> dict[str, Any]:
    """把查询参数整理成服务层入参；不合法的排序与状态值在这里拦下并说明原因。"""
    if sort not in SORTABLE_FIELDS:
        raise HTTPException(status_code=400, detail=f"暂不支持按「{sort}」排序，可选：{'、'.join(SORTABLE_FIELDS)}")
    if order not in ("asc", "desc"):
        raise HTTPException(status_code=400, detail="排序方向只支持 asc 或 desc")
    if status and status not in STATUS_ORDER:
        raise HTTPException(status_code=400, detail=f"设施状态「{status}」不在允许的状态序列里")
    return {
        "code": code,
        "name": name,
        "unit": unit,
        "section": section,
        "facility_type": facility_type,
        "status": status,
        "sort": sort,
        "order": order,
    }


@router.get("", response_model=PageResult[dict])
def list_entries(
    code: str | None = Query(default=None, description="按设施编号模糊检索"),
    name: str | None = Query(default=None, description="按设施名称模糊检索"),
    unit: str | None = Query(default=None, description="按管养单位筛选"),
    section: str | None = Query(default=None, description="按所在路段模糊检索"),
    facility_type: str | None = Query(default=None, alias="type", description="只看某类设施类型"),
    status: str | None = Query(default=None, description="正常运行、限制通行、封闭维修、已废弃"),
    sort: str = Query(default="设施编号", description="排序字段"),
    order: str = Query(default="asc", description="asc 正序 / desc 倒序"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """组合筛选设施台账：编号、名称、管养单位、路段可叠加，类型与状态精确过滤；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    filters = _parse_filters(code, name, unit, section, facility_type, status, sort, order)
    items, total = service.list_entries(**filters, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/facets")
def list_facets() -> dict[str, Any]:
    """筛选项元数据：设施类型、管养单位、所在路段的可选值与各状态数量。"""
    return service.facets()


@router.get("/export")
def export_entries(
    code: str | None = Query(default=None),
    name: str | None = Query(default=None),
    unit: str | None = Query(default=None),
    section: str | None = Query(default=None),
    facility_type: str | None = Query(default=None, alias="type"),
    status: str | None = Query(default=None),
    sort: str = Query(default="设施编号"),
    order: str = Query(default="asc"),
) -> dict[str, Any]:
    """导出设施台账清单：返回当前过滤条件下的全量数据。"""
    filters = _parse_filters(code, name, unit, section, facility_type, status, sort, order)
    items, total = service.list_entries(**filters, page=1, size=10000)
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
