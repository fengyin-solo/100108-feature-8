<template>
  <section class="page facility-detail" data-module="facility-detail">
    <header class="page-head">
      <div>
        <h2>设施明细</h2>
        <p class="page-desc">查看设施的台账信息与状态，列表展示的设施状态以本页为准。</p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="backToList">返回设施台账</button>
      </div>
    </header>

    <div v-if="loading" class="detail-box">设施明细加载中…</div>

    <div v-else-if="errorMessage" class="detail-box">
      <p class="error-text">{{ errorMessage }}</p>
      <button class="btn" type="button" @click="backToList">返回设施台账</button>
    </div>

    <template v-else-if="entry">
      <div class="detail-status">
        <span class="status-label">当前设施状态</span>
        <span class="status-tag" :data-status="statusText">{{ statusText }}</span>
      </div>

      <table class="data-table detail-table">
        <tbody>
          <tr v-for="field in detailFields" :key="field">
            <th>{{ field }}</th>
            <td>{{ entry[field] ?? '—' }}</td>
          </tr>
        </tbody>
      </table>

      <div class="detail-actions">
        <button
          v-for="action in actions"
          :key="action"
          class="btn"
          type="button"
          :disabled="saving"
          @click="runAction(action)"
        >
          {{ action }}
        </button>
      </div>
      <p v-if="actionMessage" class="action-message" :class="{ 'error-text': !lastActionOk }">{{ actionMessage }}</p>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { request } from '@/api/client'

type Entry = Record<string, string | number | null>

const ENDPOINT = '/api/facility'
const detailFields = ["设施编号", "设施名称", "设施类型", "所在路段", "管养单位", "建设年代", "设计等级", "设施状态"]
const actions = ["限制通行", "封闭维修", "恢复通行"]

const route = useRoute()
const router = useRouter()

const entry = ref<Entry | null>(null)
const loading = ref(true)
const saving = ref(false)
const errorMessage = ref('')
const actionMessage = ref('')
const lastActionOk = ref(true)

const entryId = computed(() => Number(route.params.id))
const statusText = computed(() => String(entry.value?.["设施状态"] ?? '—'))

// 明细页地址带着列表的全部筛选条件与页码，返回时原样恢复并定位回本设施。
function backToList() {
  void router.push({ path: '/facility', query: route.query })
}

async function loadEntry() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${entryId.value}`)
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`设施 ${entryId.value} 不存在或已归档`)
      }
      throw new Error('设施明细读取失败')
    }
    entry.value = await response.json()
  } catch (error) {
    entry.value = null
    errorMessage.value = error instanceof Error ? error.message : '设施明细读取失败'
  } finally {
    loading.value = false
  }
}

async function runAction(action: string) {
  saving.value = true
  actionMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${entryId.value}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    const payload = await response.json().catch(() => null)
    if (!response.ok || payload?.ok === false) {
      throw new Error(payload?.message || '设施台账动作未生效，请稍后重试')
    }
    entry.value = payload.entry ?? entry.value
    lastActionOk.value = true
    actionMessage.value = payload.message || '状态已更新'
  } catch (error) {
    lastActionOk.value = false
    actionMessage.value = error instanceof Error ? error.message : '设施台账操作失败'
  } finally {
    saving.value = false
  }
}

onMounted(loadEntry)
</script>

<style scoped>
.detail-box {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
  color: var(--muted);
}
.detail-status {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 12px;
}
.status-label { color: var(--muted); font-size: 13px; }
.status-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  background: #e8f3ff;
  color: #1f6feb;
}
.status-tag[data-status='限制通行'] { background: #fef3c7; color: #b45309; }
.status-tag[data-status='封闭维修'] { background: #fee2e2; color: #b42318; }
.status-tag[data-status='已废弃'] { background: #e5e7eb; color: #475569; }
.detail-table th {
  width: 160px;
  background: #f8fafc;
}
.detail-actions { display: flex; gap: 8px; margin-top: 14px; }
.detail-actions .btn:disabled { opacity: 0.5; cursor: not-allowed; }
.action-message { margin-top: 10px; font-size: 13px; }
</style>
