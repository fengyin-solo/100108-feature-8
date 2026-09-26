"""设施台账业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "facility"
REQUIRED_FIELDS = ["设施编号", "设施名称", "设施类型"]
OPTIONAL_FIELDS = ["所在路段", "管养单位", "建设年代", "设计等级"]
STATUS_ORDER = ["正常运行", "限制通行", "封闭维修", "已废弃"]
ACTION_RULES = {"限制通行": "限制通行", "封闭维修": "封闭维修", "恢复通行": "正常运行"}
NEGATIVE_ACTIONS: list[str] = []

# 列表允许排序的字段，避免把任意键名交给排序逻辑
SORTABLE_FIELDS = ["设施编号", "设施名称", "设施类型", "所在路段", "管养单位", "建设年代"]
# 支持模糊组合的文本筛选：查询参数名 -> 记录字段名
TEXT_FILTERS = {"code": "设施编号", "name": "设施名称", "unit": "管养单位", "section": "所在路段"}


def _present(row: dict[str, Any]) -> dict[str, Any]:
    """对外展示口径：设施状态以 status 字段为准，保证列表与详情看到的一致。"""
    item = dict(row)
    item["设施状态"] = str(row.get("status") or STATUS_ORDER[0])
    return item


class FacilityService:
    def list_entries(
        self,
        *,
        code: str | None = None,
        name: str | None = None,
        unit: str | None = None,
        section: str | None = None,
        facility_type: str | None = None,
        status: str | None = None,
        sort: str = "设施编号",
        order: str = "asc",
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        for value, field in ((code, "设施编号"), (name, "设施名称"), (unit, "管养单位"), (section, "所在路段")):
            needle = (value or "").strip()
            if needle:
                rows = [row for row in rows if needle.lower() in str(row.get(field, "")).lower()]
        if facility_type:
            rows = [row for row in rows if row.get("设施类型") == facility_type]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        rows = self._sort(rows, sort=sort, order=order)
        total = len(rows)
        start = max(page - 1, 0) * size
        return [_present(row) for row in rows[start:start + size]], total

    def facets(self) -> dict[str, Any]:
        """筛选项元数据：类型、管养单位、路段的可选值与各状态数量，给筛选栏和统计卡片用。"""
        rows = store.rows(MODULE)
        return {
            "types": sorted({str(row.get("设施类型") or "") for row in rows} - {""}),
            "units": sorted({str(row.get("管养单位") or "") for row in rows} - {""}),
            "sections": sorted({str(row.get("所在路段") or "") for row in rows} - {""}),
            "statuses": [
                {"label": label, "count": sum(1 for row in rows if row.get("status") == label)}
                for label in STATUS_ORDER
            ],
        }

    @staticmethod
    def _sort(rows: list[dict[str, Any]], *, sort: str, order: str) -> list[dict[str, Any]]:
        field = sort if sort in SORTABLE_FIELDS else "设施编号"
        keyed = sorted(rows, key=lambda row: (str(row.get(field) or ""), int(row.get("id", 0))))
        if order == "desc":
            keyed.reverse()
        return keyed

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        entry = store.find(MODULE, entry_id)
        return _present(entry) if entry is not None else None

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        for field in REQUIRED_FIELDS + OPTIONAL_FIELDS:
            if values.get(field) is not None:
                entry[field] = values.get(field)
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return _present(entry), []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"设施 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于设施台账可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return _present(entry), f"设施已{action}"
