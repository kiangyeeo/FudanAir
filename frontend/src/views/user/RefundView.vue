<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Back, Check, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { refundApi } from '@/api/refund'
import { formatCurrency } from '@/utils/format'
import { orderStatusLabel, refundTierLabel, ticketStatusLabel } from '@/utils/labels'
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
    ElMessage.warning('Enter a ticket number')
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
    ElMessage.warning('Calculate the refund fees first')
    return
  }

  try {
    await ElMessageBox.confirm(
      `Refund ticket ${quote.value.ticket_no}? Estimated refund ${formatCurrency(quote.value.refund_amount)}, fee ${formatCurrency(quote.value.fee)}.`,
      'Confirm Refund',
      {
        confirmButtonText: 'Confirm Refund',
        cancelButtonText: 'Cancel',
        type: 'warning',
      },
    )
  } catch {
    return
  }

  submitLoading.value = true
  try {
    result.value = await refundApi.refund({ ticket_no: quote.value.ticket_no })
    ElMessage.success('Refund submitted')
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
          <h1 class="page-title">Refund</h1>
          <span>Calculate fees and refund amount before submitting.</span>
        </div>
        <el-button v-if="orderNo" :icon="Back" @click="backToOrder">Back to Order</el-button>
      </div>

      <div v-if="form.ticket_no" class="ticket-readonly">
        <div class="ticket-field">
          <label>Ticket No.</label>
          <div class="ticket-value mono-num">{{ form.ticket_no }}</div>
        </div>
        <el-button type="primary" :icon="Search" :loading="quoteLoading" @click="loadQuote">Recalculate</el-button>
      </div>
      <el-alert
        v-else
        type="info"
        show-icon
        :closable="false"
        title="Open this page from Refund in Order Details so the ticket number is filled automatically."
      />
    </section>

    <section v-if="quote && quoteMatches" v-loading="quoteLoading" class="page-section">
      <h2>Refund Fee Details</h2>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="Ticket No.">{{ quote.ticket_no }}</el-descriptions-item>
        <el-descriptions-item label="Fee Tier">{{ refundTierLabel(quote.tier) }}</el-descriptions-item>
        <el-descriptions-item label="Original Paid Price">
          <span class="mono-num">{{ formatCurrency(quote.actual_price) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="Fee Rate">{{ feeRateText(quote.fee_rate) }}</el-descriptions-item>
        <el-descriptions-item label="Fee">
          <span class="mono-num danger">{{ formatCurrency(quote.fee) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="Estimated Refund">
          <span class="mono-num success">{{ formatCurrency(quote.refund_amount) }}</span>
        </el-descriptions-item>
      </el-descriptions>

      <div class="formula-box mono-num">
        <div>Fee = original paid price {{ formatCurrency(quote.actual_price) }} × fee rate {{ feeRateText(quote.fee_rate) }} = {{ formatCurrency(quote.fee) }}</div>
        <div>Refund = original paid price {{ formatCurrency(quote.actual_price) }} - fee {{ formatCurrency(quote.fee) }} = {{ formatCurrency(quote.refund_amount) }}</div>
      </div>

      <div class="actions">
        <el-button type="danger" :icon="Check" :loading="submitLoading" :disabled="!canSubmit" @click="submit">Confirm Refund</el-button>
      </div>
    </section>

    <section v-if="result" class="page-section">
      <h2>Refund Result</h2>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="Refund Record ID">{{ result.refund_id }}</el-descriptions-item>
        <el-descriptions-item label="Ticket Status">
          <el-tag type="info">{{ ticketStatusLabel(result.ticket_status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="Order Status">
          <el-tag :type="result.order_status === '已完成退款' ? 'info' : 'warning'">{{ orderStatusLabel(result.order_status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="Actual Refund">
          <span class="mono-num success">{{ formatCurrency(result.refund_amount) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="Actual Fee">
          <span class="mono-num danger">{{ formatCurrency(result.fee) }}</span>
        </el-descriptions-item>
      </el-descriptions>
      <div class="actions">
        <el-button :icon="Back" @click="backToOrder">Back to Order Details</el-button>
      </div>
    </section>
  </div>
</template>

<style scoped lang="scss">
.refund-page {
  display: grid;
  gap: 16px;
  max-width: 860px;
  padding: 20px 0 8px;
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

.ticket-readonly {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: flex-end;
  margin-top: 4px;
}

.ticket-field {
  display: grid;
  gap: 7px;
}

.ticket-field label {
  color: var(--fa-brand-dark);
  font-size: 13px;
  font-weight: 600;
}

.ticket-value {
  min-width: 260px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  padding: 0 16px;
  background: var(--fa-surface-2);
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius);
  font-size: 15px;
  font-weight: 600;
  color: var(--fa-text);
  letter-spacing: 0.02em;
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
  .ticket-value {
    min-width: 0;
    width: 100%;
  }
}
</style>
