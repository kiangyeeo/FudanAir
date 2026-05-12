<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Back, Check, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { refundApi } from '@/api/refund'
import { formatCurrency } from '@/utils/format'
import type { RefundQuote, RefundTicketResponse } from '@/types/refund'

const route = useRoute()
const router = useRouter()
const form = reactive({ ticket_no: '' })
const orderNo = ref('')
const quote = ref<RefundQuote | null>(null)
const result = ref<RefundTicketResponse | null>(null)
const quoteLoading = ref(false)
const submitLoading = ref(false)

const normalizedTicketNo = computed(() => form.ticket_no.trim())
const quoteMatches = computed(() => quote.value?.ticket_no === normalizedTicketNo.value)
const canSubmit = computed(() => Boolean(quote.value && quoteMatches.value && !result.value))

async function loadQuote() {
  const ticketNo = normalizedTicketNo.value
  if (!ticketNo) {
    ElMessage.warning('请填写客票号')
    return
  }

  quoteLoading.value = true
  result.value = null
  try {
    quote.value = await refundApi.quote({ ticket_no: ticketNo, op_type: 'refund' })
  } finally {
    quoteLoading.value = false
  }
}

async function submit() {
  if (!canSubmit.value || !quote.value) {
    ElMessage.warning('请先完成退票费用试算')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认退票 ${quote.value.ticket_no}？预计退款 ${formatCurrency(quote.value.refund_amount)}，手续费 ${formatCurrency(quote.value.fee)}。`,
      '确认退票',
      {
        confirmButtonText: '确认退票',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
  } catch {
    return
  }

  submitLoading.value = true
  try {
    result.value = await refundApi.refund({ ticket_no: quote.value.ticket_no })
    ElMessage.success('退票申请已提交')
  } finally {
    submitLoading.value = false
  }
}

function backToOrder() {
  if (orderNo.value) {
    router.push({ name: 'order-detail', params: { orderNo: orderNo.value } })
    return
  }
  router.push({ name: 'orders' })
}

function feeRateText(rate?: number) {
  if (rate === undefined || Number.isNaN(rate)) {
    return '--'
  }
  return `${(rate * 100).toFixed(0)}%`
}

function queryText(key: string): string | null {
  const value = route.query[key]
  if (Array.isArray(value)) {
    return value[0] ?? null
  }
  return value ?? null
}

watch(
  () => form.ticket_no,
  () => {
    quote.value = null
    result.value = null
  },
)

onMounted(() => {
  form.ticket_no = queryText('ticket_no') ?? ''
  orderNo.value = queryText('order_no') ?? ''
  if (form.ticket_no) {
    void loadQuote()
  }
})
</script>

<template>
  <div class="page-shell refund-page">
    <section class="page-section">
      <div class="page-heading">
        <div>
          <h1 class="page-title">退票</h1>
          <span>先试算手续费和退款金额，再确认提交。</span>
        </div>
        <el-button v-if="orderNo" :icon="Back" @click="backToOrder">返回订单</el-button>
      </div>

      <el-form :model="form" label-position="top" class="ticket-form">
        <el-form-item label="客票号">
          <el-input v-model="form.ticket_no" placeholder="输入需要退票的客票号" clearable />
        </el-form-item>
        <el-form-item label=" ">
          <el-button type="primary" :icon="Search" :loading="quoteLoading" @click="loadQuote">试算费用</el-button>
        </el-form-item>
      </el-form>
    </section>

    <section v-if="quote && quoteMatches" v-loading="quoteLoading" class="page-section">
      <h2>退票费用明细</h2>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="客票号">{{ quote.ticket_no }}</el-descriptions-item>
        <el-descriptions-item label="费率档位">{{ quote.tier }}</el-descriptions-item>
        <el-descriptions-item label="原成交价">
          <span class="mono-num">{{ formatCurrency(quote.actual_price) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="手续费率">{{ feeRateText(quote.fee_rate) }}</el-descriptions-item>
        <el-descriptions-item label="手续费">
          <span class="mono-num danger">{{ formatCurrency(quote.fee) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="预计退款">
          <span class="mono-num success">{{ formatCurrency(quote.refund_amount) }}</span>
        </el-descriptions-item>
      </el-descriptions>

      <div class="formula-box mono-num">
        <div>手续费 = 原成交价 {{ formatCurrency(quote.actual_price) }} × 手续费率 {{ feeRateText(quote.fee_rate) }} = {{ formatCurrency(quote.fee) }}</div>
        <div>退款金额 = 原成交价 {{ formatCurrency(quote.actual_price) }} - 手续费 {{ formatCurrency(quote.fee) }} = {{ formatCurrency(quote.refund_amount) }}</div>
      </div>

      <div class="actions">
        <el-button type="danger" :icon="Check" :loading="submitLoading" :disabled="!canSubmit" @click="submit">确认退票</el-button>
      </div>
    </section>

    <section v-if="result" class="page-section">
      <h2>退票结果</h2>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="退票记录 ID">{{ result.refund_id }}</el-descriptions-item>
        <el-descriptions-item label="客票状态">
          <el-tag type="info">{{ result.ticket_status }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="订单状态">
          <el-tag :type="result.order_status === '已完成退款' ? 'info' : 'warning'">{{ result.order_status }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="实际退款">
          <span class="mono-num success">{{ formatCurrency(result.refund_amount) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="实际手续费">
          <span class="mono-num danger">{{ formatCurrency(result.fee) }}</span>
        </el-descriptions-item>
      </el-descriptions>
      <div class="actions">
        <el-button :icon="Back" @click="backToOrder">返回订单详情</el-button>
      </div>
    </section>
  </div>
</template>

<style scoped lang="scss">
.refund-page {
  display: grid;
  gap: 16px;
  max-width: 860px;
}

.page-heading {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
}

.page-heading span,
.formula-box {
  color: var(--fa-text-secondary);
  font-size: 13px;
}

.ticket-form {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) auto;
  gap: 12px;
  align-items: end;
}

h2 {
  margin: 0 0 12px;
  font-size: 16px;
}

.formula-box {
  display: grid;
  gap: 6px;
  margin-top: 12px;
  padding: 12px;
  background: var(--fa-bg);
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius);
}

.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

.danger {
  color: var(--fa-danger);
  font-weight: 700;
}

.success {
  color: #1f8f4d;
  font-weight: 700;
}

@media (max-width: 760px) {
  .ticket-form {
    grid-template-columns: 1fr;
  }
}
</style>
