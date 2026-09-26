<template>
  <section class="page" data-module="facility">
    <header class="page-head">
      <div>
        <h2>设施台账管理</h2>
        <p class="page-desc">维护设施，围绕设施编号、设施名称、设施类型、所在路段做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记设施</button>
        <button class="btn" type="button" @click="exportRows">导出设施台账清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="submitSearch">
      <label class="filter-item">
        <span>设施编号</span>
        <input v-model.trim="draft.code" placeholder="按设施编号检索" />
      </label>
      <label class="filter-item">
        <span>设施名称</span>
        <input v-model.trim="draft.name" placeholder="按设施名称检索" />
      </label>
      <label class="filter-item">
        <span>管养单位</span>
        <input v-model.trim="draft.unit" placeholder="按管养单位检索" list="facility-unit-options" />
        <datalist id="facility-unit-options">
          <option v-for="unit in meta.units" :key="unit" :value="unit" />
        </datalist>
      </label>
      <label class="filter-item">
        <span>设施类型</span>
        <select v-model="draft.type">
          <option value="">全部类型</option>
          <option v-for="type in meta.types" :key="type" :value="type">{{ type }}</option>
        </select>
      </label>
      <label class="filter-item">
        <span>设施状态</span>
        <select v-model="draft.status">
          <option value="">全部状态</option>
          <option v-for="status in meta.statuses" :key="status" :value="status">{{ status }}</option>
        </select>
      </label>
      <label class="filter-item">
        <span>排序字段</span>
        <select v-model="draft.sortBy">
          <option v-for="field in sortFields" :key="field" :value="field">按{{ field }}</option>
        </select>
      </label>
      <label class="filter-item">
        <span>排序方向</span>
        <select v-model="draft.order">
          <option value="asc">正序</option>
          <option value="desc">倒序</option>
        </select>
      </label>
      <button class="btn primary" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="group in groups" :key="group.key">
          <tr
            v-if="group.rows.length > 1"
            class="group-row"
            :class="{ expanded: expandedNames.has(group.name) }"
            @click="toggleGroup(group.name)"
          >
            <td :colspan="columns.length + 1">
              <span class="group-toggle">{{ expandedNames.has(group.name) ? '▼' : '▶' }}</span>
              <span class="group-name">{{ group.name }}</span>
              <span class="group-meta">同名设施 {{ group.rows.length }} 条</span>
              <span class="group-roads">所在路段：{{ group.roads.join('；') }}</span>
            </td>
          </tr>
          <tr
            v-for="row in visibleRows(group)"
            :key="String(row.id)"
            :data-row-id="row.id"
            :class="{ 'focus-row': focusId === row.id }"
          >
            <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
            <td class="row-actions">
              <button class="link" type="button" @click="openDetail(row)">查看详情</button>
              <button
                v-for="action in actions"
                :key="action"
                class="link"
                type="button"
                @click="runAction(action, row)"
              >
                {{ action }}
              </button>
            </td>
          </tr>
        </template>
        <tr v-if="!loading && !rows.length && total === 0">
          <td :colspan="columns.length + 1" class="empty-state">
            <template v-if="activeFilterCount > 0">
              <p class="empty-title">没有找到符合条件的设施</p>
              <p class="empty-desc">当前筛选：{{ activeFilterText }}。可放宽条件后重新查询，或重置全部筛选。</p>
              <div class="empty-actions">
                <button class="btn" type="button" @click="goFirstPage">回到第一页</button>
                <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
              </div>
            </template>
            <template v-else>
              <p class="empty-title">暂无设施台账数据</p>
              <p class="empty-desc">可先登记设施，再回来查看台账清单。</p>
            </template>
          </td>
        </tr>
        <tr v-else-if="!loading && rows.length === 0">
          <td :colspan="columns.length + 1" class="empty-state">
            <p class="empty-title">第 {{ page }} 页没有记录</p>
            <p class="empty-desc">当前筛选共命中 {{ total }} 条，页码可能超出范围。</p>
            <div class="empty-actions">
              <button class="btn" type="button" @click="goFirstPage">回到第一页</button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条设施台账记录，第 {{ page }} / {{ totalPages }} 页</span>
      <span class="pager">
        <button class="btn" type="button" :disabled="page <= 1 || loading" @click="gotoPage(1)">首页</button>
        <button class="btn" type="button" :disabled="page <= 1 || loading" @click="gotoPage(page - 1)">上一页</button>
        <button
          class="btn"
          type="button"
          :disabled="page >= totalPages || loading"
          @click="gotoPage(page + 1)"
        >下一页</button>
        <button
          class="btn"
          type="button"
          :disabled="page >= totalPages || loading"
          @click="gotoPage(totalPages)"
        >末页</button>
      </span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>

interface ListPayload {
  items: Row[]
  total: number
  page: number
  size: number
}

interface MetaPayload {
  types: string[]
  units: string[]
  statuses: string[]
  stats: { label: string; value: number }[]
}

interface Group {
  key: string
  name: string
  rows: Row[]
  roads: string[]
}

const ENDPOINT = '/api/facility'
const PAGE_SIZE = 10
const columns = ["设施编号", "设施名称", "设施类型", "所在路段", "管养单位", "建设年代", "设计等级", "设施状态"]
const sortFields = ["设施编号", "设施名称", "设施类型", "所在路段", "管养单位", "建设年代"]
const actions = ["限制通行", "封闭维修", "恢复通行"]
const FILTER_QUERY_KEYS = ["code", "name", "unit", "type", "status", "sortBy", "order"]

const route = useRoute()
const router = useRouter()

const rows = ref<Row[]>([])
const total = ref(0)
const loading = ref(false)
const errorMessage = ref('')
const focusId = ref<number | null>(null)
const expandedNames = ref<Set<string>>(new Set())
const meta = ref<MetaPayload>({ types: [], units: [], statuses: [], stats: [] })
const stats = computed(() =>
  meta.value.stats.length
    ? meta.value.stats
    : [
        { label: "正常设施", value: 0 },
        { label: "限制通行设施", value: 0 },
        { label: "封闭维修设施", value: 0 },
        { label: "已废弃设施", value: 0 },
      ],
)

const draft = reactive({
  code: '',
  name: '',
  unit: '',
  type: '',
  status: '',
  sortBy: '设施编号',
  order: 'asc',
})

const page = computed(() => readInt(route.query.page, 1))
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

const groups = computed<Group[]>(() => {
  const map = new Map<string, Group>()
  for (const row of rows.value) {
    const name = String(row["设施名称"] ?? '')
    let group = map.get(name)
    if (!group) {
      group = { key: name, name, rows: [], roads: [] }
      map.set(name, group)
    }
    group.rows.push(row)
    const road = String(row["所在路段"] ?? '')
    if (road && !group.roads.includes(road)) {
      group.roads.push(road)
    }
  }
  return [...map.values()]
})

const activeFilterEntries = computed(() => {
  const labels: Record<string, string> = {
    code: '设施编号',
    name: '设施名称',
    unit: '管养单位',
    type: '设施类型',
    status: '设施状态',
  }
  const entries: string[] = []
  for (const key of FILTER_QUERY_KEYS) {
    const raw = route.query[key]
    const value = Array.isArray(raw) ? raw[0] : raw
    if (typeof value === 'string' && value.trim()) {
      if (key === 'sortBy') {
        if (value !== '设施编号') entries.push(`排序：按${value}`)
      } else if (key === 'order') {
        if (value === 'desc') entries.push('排序：倒序')
      } else {
        entries.push(`${labels[key]}=${value}`)
      }
    }
  }
  return entries
})
const activeFilterCount = computed(() => {
  const keys = ["code", "name", "unit", "type", "status"]
  return keys.filter((key) => {
    const raw = route.query[key]
    const value = Array.isArray(raw) ? raw[0] : raw
    return typeof value === 'string' && value.trim()
  }).length
})
const activeFilterText = computed(() => activeFilterEntries.value.join('，') || '无')

function readInt(value: unknown, fallback: number): number {
  const parsed = Number.parseInt(String(value ?? ''), 10)
  return Number.isFinite(parsed) && parsed >= 1 ? parsed : fallback
}

function syncDraftFromQuery() {
  const q = route.query
  draft.code = String(q.code ?? '')
  draft.name = String(q.name ?? '')
  draft.unit = String(q.unit ?? '')
  draft.type = String(q.type ?? '')
  draft.status = String(q.status ?? '')
  draft.sortBy = sortFields.includes(String(q.sortBy)) ? String(q.sortBy) : '设施编号'
  draft.order = q.order === 'desc' ? 'desc' : 'asc'
}

function listSignature() {
  const q = route.query
  return ["code", "name", "unit", "type", "status", "sortBy", "order", "page"]
    .map((key) => `${key}=${Array.isArray(q[key]) ? q[key][0] : q[key] ?? ''}`)
    .join('&')
}

let lastSignature = ''

function buildQuery(pageOverride?: number, extra?: Record<string, string | null>) {
  const query: Record<string, string> = {}
  const valueMap: Record<string, string> = {
    code: draft.code.trim(),
    name: draft.name.trim(),
    unit: draft.unit.trim(),
    type: draft.type,
    status: draft.status,
    sortBy: draft.sortBy,
    order: draft.order,
  }
  for (const [key, value] of Object.entries(valueMap)) {
    if (value && !(key === 'sortBy' && value === '设施编号') && !(key === 'order' && value === 'asc')) {
      query[key] = value
    }
  }
  const targetPage = pageOverride ?? page.value
  if (targetPage > 1) {
    query.page = String(targetPage)
  }
  if (extra) {
    for (const [key, value] of Object.entries(extra)) {
      if (value === null) {
        delete query[key]
      } else {
        query[key] = value
      }
    }
  }
  return query
}

// 筛选条件与排序写进地址栏：翻页后改条件仍停留在当前页，从详情返回时状态原样恢复。
function submitSearch() {
  focusId.value = null
  void router.push({ path: route.path, query: buildQuery() })
}

function resetFilters() {
  focusId.value = null
  void router.push({ path: route.path })
}

function gotoPage(target: number) {
  focusId.value = null
  void router.push({ path: route.path, query: buildQuery(target) })
}

function goFirstPage() {
  gotoPage(1)
}

function toggleGroup(name: string) {
  if (expandedNames.value.has(name)) {
    expandedNames.value.delete(name)
  } else {
    expandedNames.value.add(name)
  }
}

function visibleRows(group: Group): Row[] {
  return group.rows.length === 1 || expandedNames.value.has(group.name) ? group.rows : []
}

function locateRow(id: number) {
  const target = rows.value.find((row) => Number(row.id) === id)
  if (!target) {
    return
  }
  const name = String(target["设施名称"] ?? '')
  const sameName = rows.value.filter((row) => String(row["设施名称"] ?? '') === name)
  // 同名记录分组折叠时自动展开，再滚动定位到对应路段那一条。
  if (sameName.length > 1) {
    expandedNames.value.add(name)
  }
  focusId.value = id
  requestAnimationFrame(() => {
    const element = document.querySelector(`tr[data-row-id="${id}"]`)
    element?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  })
}

function openDetail(row: Row) {
  void router.push({
    path: `${ENDPOINT}/${row.id}`,
    query: buildQuery(page.value, { focus: String(row.id) }),
  })
}

function exportRows() {
  const query = new URLSearchParams(buildQuery()).toString()
  window.open(`${ENDPOINT}/export${query ? `?${query}` : ''}`, '_blank')
}

function openCreate() {
  errorMessage.value = '设施登记入口尚未接入审批流'
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    if (!response.ok) {
      throw new Error('设施台账动作未生效，请稍后重试')
    }
    const payload = await response.json()
    if (payload && payload.ok === false) {
      throw new Error(payload.message || '设施台账动作未生效')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '设施台账操作失败'
  }
}

async function loadMeta() {
  try {
    const response = await request(`${ENDPOINT}/meta`)
    if (response.ok) {
      meta.value = await response.json()
    }
  } catch {
    // 元数据只影响下拉与统计卡，失败时不阻塞列表读取。
  }
}

async function reload() {
  loading.value = true
  errorMessage.value = ''
  const q = route.query
  const params = new URLSearchParams()
  for (const key of ["code", "name", "unit", "type", "status", "sortBy", "order"]) {
    const raw = q[key]
    const value = Array.isArray(raw) ? raw[0] : raw
    if (typeof value === 'string' && value) {
      params.set(key === 'type' ? 'facility_type' : key, value)
    }
  }
  params.set('page', String(page.value))
  params.set('size', String(PAGE_SIZE))
  try {
    const response = await request(`${ENDPOINT}?${params.toString()}`)
    if (!response.ok) {
      throw new Error('设施列表读取失败')
    }
    const payload: ListPayload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    rows.value = []
    total.value = 0
    errorMessage.value = error instanceof Error ? error.message : '设施台账列表读取失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => route.query,
  (query) => {
    syncDraftFromQuery()
    const signature = listSignature()
    if (signature !== lastSignature) {
      lastSignature = signature
      void reload().then(() => {
        const focus = readInt(query.focus, 0)
        if (focus) {
          locateRow(focus)
        }
      })
    } else {
      const focus = readInt(query.focus, 0)
      if (focus && focus !== focusId.value) {
        locateRow(focus)
      }
    }
  },
  { immediate: true, deep: true },
)

onMounted(() => {
  void loadMeta()
})
</script>

<style scoped>
.page-actions { display: flex; gap: 8px; }
.filter-item select { min-width: 110px; }
.group-row {
  background: #f1f5fb;
  cursor: pointer;
  font-weight: 600;
}
.group-row:hover { background: #e6eef9; }
.group-toggle { display: inline-block; width: 16px; color: var(--brand); }
.group-meta { margin-left: 12px; font-size: 12px; color: var(--brand); font-weight: 400; }
.group-roads {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: var(--muted);
  font-weight: 400;
}
.focus-row td { background: #fff7d6; transition: background 1s ease; }
.empty-state { text-align: center; color: var(--muted); padding: 20px 10px; }
.empty-title { margin: 0 0 6px; font-size: 14px; color: #334155; }
.empty-desc { margin: 0 0 10px; font-size: 12px; }
.empty-actions { display: flex; gap: 8px; justify-content: center; }
.pager { display: flex; gap: 6px; }
.pager .btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
