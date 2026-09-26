"""设施台账业务规则：状态流转、字段校验、组合筛选与排序口径都收在这里。"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "facility"
REQUIRED_FIELDS = ["设施编号", "设施名称", "设施类型"]
STATUS_ORDER = ["正常运行", "限制通行", "封闭维修", "已废弃"]
# 列表允许排序的字段；默认按设施编号正序。
SORT_FIELDS = ["设施编号", "设施名称", "设施类型", "所在路段", "管养单位", "建设年代"]
ACTION_RULES = {"限制通行": "限制通行", "封闭维修": "封闭维修", "恢复通行": "正常运行"}
NEGATIVE_ACTIONS = []
# 统计卡片与内部状态的对应关系。
STAT_LABELS = [
    ("正常运行", "正常设施"),
    ("限制通行", "限制通行设施"),
    ("封闭维修", "封闭维修设施"),
    ("已废弃", "已废弃设施"),
]


def _present(row: dict[str, Any]) -> dict[str, Any]:
    """统一对外结构：列表与详情都从这里出，保证「设施状态」与内部 status 始终一致。"""
    item = dict(row)
    item["设施状态"] = row.get("status")
    return item


class FacilityService:
    def list_entries(
        self,
        *,
        code: str | None = None,
        name: str | None = None,
        unit: str | None = None,
        facility_type: str | None = None,
        status: str | None = None,
        sort_by: str = "设施编号",
        order: str = "asc",
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = self._filter_rows(
            code=code, name=name, unit=unit, facility_type=facility_type, status=status
        )
        rows.sort(
            key=lambda row: str(row.get(sort_by) or ""),
            reverse=order == "desc",
        )
        total = len(rows)
        start = max(page - 1, 0) * size
        page_rows = [_present(row) for row in rows[start:start + size]]
        return page_rows, total

    def meta(self) -> dict[str, Any]:
        """筛选下拉项与状态统计：类型/单位去重，状态按全量数据计数。"""
        rows = store.rows(MODULE)
        types = sorted({str(row.get("设施类型") or "") for row in rows if row.get("设施类型")})
        units = sorted({str(row.get("管养单位") or "") for row in rows if row.get("管养单位")})
        counts = {label: 0 for label, _ in STAT_LABELS}
        for row in rows:
            label = str(row.get("status") or "")
            if label in counts:
                counts[label] += 1
        stats = [
            {"label": title, "value": counts[label]}
            for label, title in STAT_LABELS
        ]
        return {"types": types, "units": units, "statuses": list(STATUS_ORDER), "stats": stats}

    def _filter_rows(
        self,
        *,
        code: str | None,
        name: str | None,
        unit: str | None,
        facility_type: str | None,
        status: str | None,
    ) -> list[dict[str, Any]]:
        rows = store.rows(MODULE)
        if code:
            rows = [row for row in rows if code in str(row.get("设施编号", ""))]
        if name:
            rows = [row for row in rows if name in str(row.get("设施名称", ""))]
        if unit:
            rows = [row for row in rows if unit in str(row.get("管养单位", ""))]
        if facility_type:
            rows = [row for row in rows if row.get("设施类型") == facility_type]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        return rows

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        entry = store.find(MODULE, entry_id)
        return _present(entry) if entry is not None else None

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = STATUS_ORDER[0]
        entry["设施状态"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

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
        entry["设施状态"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"设施已{action}"
