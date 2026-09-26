<template>
  <section class="page" data-module="facility-detail">
    <header class="page-head">
      <div>
        <h2>设施详情</h2>
        <p class="page-desc">设施 {{ entry?.['设施编号'] ?? route.params.id }} 的台账明细与状态流转，状态与列表页保持一致。</p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="backToList">返回设施台账列表</button>
      </div>
    </header>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <template v-if="entry">
      <dl class="detail-grid">
        <div v-for="field in fields" :key="field" class="detail-item">
          <dt>{{ field }}</dt>
          <dd>
            <span v-if="field === '设施状态'" class="status-tag" :data-status="entry[field]">
              {{ entry[field] ?? '—' }}
            </span>
            <template v-else>{{ entry[field] ?? '—' }}</template>
          </dd>
        </div>
      </dl>

      <div class="detail-actions">
        <button
          v-for="action in actions"
          :key="action"
          class="btn"
          type="button"
          @click="runAction(action)"
        >
          {{ action }}
        </button>
      </div>
      <p v-if="actionMessage" class="action-message">{{ actionMessage }}</p>
    </template>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>

const ENDPOINT = '/api/facility'
const fields = ["设施编号", "设施名称", "设施类型", "所在路段", "管养单位", "建设年代", "设计等级", "设施状态"]
const actions = ["限制通行", "封闭维修", "恢复通行"]

const route = useRoute()
const router = useRouter()

const entry = ref<Row | null>(null)
const errorMessage = ref('')
const actionMessage = ref('')

// 列表页把筛选条件与页码放在 query 里带过来，返回时原样带回列表
function backToList() {
  void router.push({ path: '/facility', query: route.query })
}

async function loadDetail() {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${route.params.id}`)
    if (response.status === 404) {
      entry.value = null
      errorMessage.value = `设施 ${String(route.params.id)} 不存在或已归档`
      return
    }
    if (!response.ok) {
      throw new Error('设施详情读取失败')
    }
    entry.value = await response.json()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '设施详情读取失败'
  }
}

async function runAction(action: string) {
  actionMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${route.params.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || payload.detail || '设施台账动作未生效，请稍后重试')
    }
    actionMessage.value = payload.message
    if (payload.entry) {
      entry.value = payload.entry
    }
  } catch (error) {
    actionMessage.value = error instanceof Error ? error.message : '设施台账操作失败'
  }
}

onMounted(loadDetail)
</script>
