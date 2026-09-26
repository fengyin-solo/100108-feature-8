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

    <form class="filter-bar" @submit.prevent="applyFilters">
      <label class="filter-item">
        <span>设施编号</span>
        <input v-model.trim="filters.code" placeholder="如 FACI-0007" />
      </label>
      <label class="filter-item">
        <span>设施名称</span>
        <input v-model.trim="filters.name" placeholder="按设施名称检索" />
      </label>
      <label class="filter-item">
        <span>管养单位</span>
        <select v-model="filters.unit">
          <option value="">全部单位</option>
          <option v-for="unit in facets.units" :key="unit" :value="unit">{{ unit }}</option>
        </select>
      </label>
      <label class="filter-item">
        <span>设施类型</span>
        <select v-model="filters.type">
          <option value="">全部类型</option>
          <option v-for="item in facets.types" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <label class="filter-item">
        <span>所在路段</span>
        <input v-model.trim="filters.section" list="facility-sections" placeholder="如 人民路" />
        <datalist id="facility-sections">
          <option v-for="item in facets.sections" :key="item" :value="item" />
        </datalist>
      </label>
      <label class="filter-item">
        <span>设施状态</span>
        <select v-model="filters.status">
          <option value="">全部状态</option>
          <option v-for="item in statuses" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th
            v-for="column in columns"
            :key="column"
            :class="{ sortable: isSortable(column) }"
            @click="isSortable(column) && toggleSort(column)"
          >
            {{ column }}
            <span v-if="isSortable(column)" class="sort-mark">{{ sortMark(column) }}</span>
          </th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="group in groups" :key="group.name">
          <tr v-if="group.rows.length > 1" class="group-row" @click="toggleGroup(group.name)">
            <td :colspan="columns.length + 1">
              <span class="group-toggle">{{ isExpanded(group.name) ? '▼' : '▶' }}</span>
              <strong>{{ group.name }}</strong>
              <span class="group-meta">
                共 {{ group.rows.length }} 条记录 · 分布路段：{{ group.sections.join('、') }}
              </span>
              <span class="group-hint">{{ isExpanded(group.name) ? '点击收起' : '点击展开并定位路段' }}</span>
            </td>
          </tr>
          <tr
            v-for="row in visibleRows(group)"
            :key="String(row.id)"
            :class="{ 'child-row': group.rows.length > 1 }"
          >
            <td v-for="column in columns" :key="column">
              <span v-if="column === '设施状态'" class="status-tag" :data-status="row[column]">
                {{ row[column] ?? '—' }}
              </span>
              <template v-else-if="column === '所在路段'">
                {{ row[column] ?? '—' }}
                <button class="link locate-link" type="button" @click="locateSection(row)">定位路段</button>
              </template>
              <template v-else>{{ row[column] ?? '—' }}</template>
            </td>
            <td class="row-actions">
              <button class="link" type="button" @click="openDetail(row)">详情</button>
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
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">
            <template v-if="hasActiveFilters">
              未找到符合{{ activeFilterText }}的设施记录。当前筛选条件已保留，可调整后重新查询。
            </template>
            <template v-else>暂无设施台账数据，可先登记设施</template>
          </td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条设施台账记录</span>
      <div class="pager">
        <label class="pager-size">
          每页
          <select v-model.number="size" @change="syncQuery">
            <option v-for="option in pageSizes" :key="option" :value="option">{{ option }}</option>
          </select>
          条
        </label>
        <button class="btn" type="button" :disabled="page <= 1" @click="goPage(page - 1)">上一页</button>
        <span class="pager-info">第 {{ page }} / {{ maxPage }} 页</span>
        <button class="btn" type="button" :disabled="page >= maxPage" @click="goPage(page + 1)">下一页</button>
      </div>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>
type Facets = {
  types: string[]
  units: string[]
  sections: string[]
  statuses: { label: string; count: number }[]
}
type Group = { name: string; rows: Row[]; sections: string[] }

const ENDPOINT = '/api/facility'
const columns = ["设施编号", "设施名称", "设施类型", "所在路段", "管养单位", "建设年代", "设计等级", "设施状态"]
const sortableColumns = ["设施编号", "设施名称", "设施类型", "所在路段", "管养单位", "建设年代"]
const actions = ["限制通行", "封闭维修", "恢复通行"]
const statuses = ["正常运行", "限制通行", "封闭维修", "已废弃"]
const pageSizes = [10, 20, 50]

const route = useRoute()
const router = useRouter()

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const facets = ref<Facets>({ types: [], units: [], sections: [], statuses: [] })
const filters = reactive({ code: '', name: '', unit: '', type: '', section: '', status: '' })
const sortField = ref('设施编号')
const sortOrder = ref<'asc' | 'desc'>('asc')
const page = ref(1)
const size = ref(20)
const expanded = ref<Set<string>>(new Set())

const stats = computed(() => {
  const counts = new Map(facets.value.statuses.map((item) => [item.label, item.count]))
  return [
    { label: '正常设施', value: counts.get('正常运行') ?? 0 },
    { label: '限制通行设施', value: counts.get('限制通行') ?? 0 },
    { label: '封闭维修设施', value: counts.get('封闭维修') ?? 0 },
  ]
})

const maxPage = computed(() => Math.max(1, Math.ceil(total.value / size.value)))

const groups = computed<Group[]>(() => {
  const map = new Map<string, Row[]>()
  for (const row of rows.value) {
    const key = String(row['设施名称'] ?? '未命名设施')
    const list = map.get(key)
    if (list) {
      list.push(row)
    } else {
      map.set(key, [row])
    }
  }
  return [...map.entries()].map(([name, items]) => ({
    name,
    rows: items,
    sections: [...new Set(items.map((item) => String(item['所在路段'] ?? '—')))],
  }))
})

const activeFilterText = computed(() => {
  const parts: string[] = []
  if (filters.code) parts.push(`设施编号「${filters.code}」`)
  if (filters.name) parts.push(`设施名称「${filters.name}」`)
  if (filters.unit) parts.push(`管养单位「${filters.unit}」`)
  if (filters.type) parts.push(`设施类型「${filters.type}」`)
  if (filters.section) parts.push(`所在路段「${filters.section}」`)
  if (filters.status) parts.push(`设施状态「${filters.status}」`)
  return parts.join('、')
})
const hasActiveFilters = computed(() => activeFilterText.value.length > 0)

function buildQuery() {
  const query: Record<string, string> = {}
  if (filters.code) query.code = filters.code
  if (filters.name) query.name = filters.name
  if (filters.unit) query.unit = filters.unit
  if (filters.type) query.type = filters.type
  if (filters.section) query.section = filters.section
  if (filters.status) query.status = filters.status
  query.sort = sortField.value
  query.order = sortOrder.value
  query.page = String(page.value)
  query.size = String(size.value)
  return query
}

function readQuery() {
  const take = (key: string) => {
    const value = route.query[key]
    return typeof value === 'string' ? value : ''
  }
  filters.code = take('code')
  filters.name = take('name')
  filters.unit = take('unit')
  filters.type = take('type')
  filters.section = take('section')
  filters.status = take('status')
  const sortValue = take('sort')
  sortField.value = sortableColumns.includes(sortValue) ? sortValue : '设施编号'
  sortOrder.value = take('order') === 'desc' ? 'desc' : 'asc'
  const pageValue = Number(take('page'))
  page.value = Number.isInteger(pageValue) && pageValue > 0 ? pageValue : 1
  const sizeValue = Number(take('size'))
  size.value = pageSizes.includes(sizeValue) ? sizeValue : 20
}

// 筛选、排序、页码都写回地址栏：从详情页返回时按 URL 原样恢复
function syncQuery() {
  const next = buildQuery()
  if (JSON.stringify(next) === JSON.stringify(route.query)) {
    void reload()
    return
  }
  void router.replace({ query: next })
}

watch(
  () => route.query,
  () => {
    readQuery()
    void reload()
  },
  { immediate: true },
)

// 查询与翻页都保留当前页码；只有页码超出结果范围时才收敛到最后一页
function applyFilters() {
  syncQuery()
}

function resetFilters() {
  filters.code = ''
  filters.name = ''
  filters.unit = ''
  filters.type = ''
  filters.section = ''
  filters.status = ''
  syncQuery()
}

function isSortable(column: string) {
  return sortableColumns.includes(column)
}

function sortMark(column: string) {
  if (sortField.value !== column) return '↕'
  return sortOrder.value === 'asc' ? '▲' : '▼'
}

function toggleSort(column: string) {
  if (sortField.value === column) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = column
    sortOrder.value = 'asc'
  }
  syncQuery()
}

function goPage(target: number) {
  page.value = Math.min(Math.max(target, 1), maxPage.value)
  syncQuery()
}

function toggleGroup(name: string) {
  const next = new Set(expanded.value)
  if (next.has(name)) {
    next.delete(name)
  } else {
    next.add(name)
  }
  expanded.value = next
}

function isExpanded(name: string) {
  // 按名称检索时同名分组默认展开，避免命中结果被折叠藏起来
  if (filters.name && name.includes(filters.name)) return true
  return expanded.value.has(name)
}

function visibleRows(group: Group) {
  if (group.rows.length <= 1) return group.rows
  return isExpanded(group.name) ? group.rows : []
}

function locateSection(row: Row) {
  filters.section = String(row['所在路段'] ?? '')
  syncQuery()
}

function openDetail(row: Row) {
  void router.push({ name: 'facility-detail', params: { id: String(row.id) }, query: buildQuery() })
}

function exportRows() {
  const query = buildQuery()
  delete query.page
  delete query.size
  window.open(`${ENDPOINT}/export?${new URLSearchParams(query)}`, '_blank')
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
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || payload.detail || '设施台账动作未生效，请稍后重试')
    }
    await Promise.all([reload(), loadFacets()])
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '设施台账操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(buildQuery()).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error('设施列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    if (total.value > 0 && page.value > maxPage.value) {
      page.value = maxPage.value
      syncQuery()
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '设施台账列表读取失败'
  }
}

async function loadFacets() {
  try {
    const response = await request(`${ENDPOINT}/facets`)
    if (!response.ok) {
      throw new Error('筛选项读取失败')
    }
    facets.value = await response.json()
  } catch {
    facets.value = { types: [], units: [], sections: [], statuses: [] }
  }
}

onMounted(loadFacets)
</script>
