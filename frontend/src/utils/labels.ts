import type { CabinClass, FareType } from '@/types/common'
import type { InstanceStatus } from '@/types/flight'
import type { OrderStatus, TicketStatus } from '@/types/order'

const orderStatusLabels: Record<OrderStatus, string> = {
  待支付: 'Pending Payment',
  已支付: 'Paid',
  已取消: 'Canceled',
  已完成: 'Completed',
  部分退款: 'Partially Refunded',
  已完成退款: 'Refunded',
}

const ticketStatusLabels: Record<TicketStatus, string> = {
  有效: 'Active',
  已退: 'Refunded',
  已改签作废: 'Voided by Change',
  已使用: 'Used',
}

const instanceStatusLabels: Record<InstanceStatus, string> = {
  计划: 'Scheduled',
  可订: 'Bookable',
  已起飞: 'Departed',
  已到达: 'Arrived',
  已取消: 'Canceled',
}

const cabinClassLabels: Record<CabinClass, string> = {
  经济舱: 'Economy',
  头等舱: 'First Class',
}

const fareTypeLabels: Record<string, string> = {
  标准: 'Standard',
  特价: 'Discount',
}

const operationLabels: Record<string, string> = {
  退票: 'Refund',
  改签: 'Change',
  refund: 'Refund',
  change: 'Change',
}

const adjustmentLabels: Record<string, string> = {
  起飞时间已调整: 'Departure Time Changed',
  降落时间已调整: 'Arrival Time Changed',
  起飞机场已调整: 'Departure Airport Changed',
  降落机场已调整: 'Arrival Airport Changed',
}

function fallbackLabel(value?: string | null) {
  return value || '--'
}

export function orderStatusLabel(status?: string | null) {
  return (status && orderStatusLabels[status as OrderStatus]) || fallbackLabel(status)
}

export function ticketStatusLabel(status?: string | null) {
  return (status && ticketStatusLabels[status as TicketStatus]) || fallbackLabel(status)
}

export function instanceStatusLabel(status?: string | null) {
  return (status && instanceStatusLabels[status as InstanceStatus]) || fallbackLabel(status)
}

export function cabinClassLabel(cabinClass?: string | null) {
  return (cabinClass && cabinClassLabels[cabinClass as CabinClass]) || fallbackLabel(cabinClass)
}

export function fareTypeLabel(fareType?: string | null) {
  return (fareType && fareTypeLabels[fareType]) || fallbackLabel(fareType)
}

export function operationLabel(operation?: string | null) {
  return (operation && operationLabels[operation]) || fallbackLabel(operation)
}

export function adjustmentLabel(label?: string | null) {
  return (label && adjustmentLabels[label]) || fallbackLabel(label)
}

export function refundTierLabel(tier?: string | null) {
  if (!tier) {
    return '--'
  }
  return tier
    .replace('≥', '>= ')
    .replace('<', '< ')
    .replace('天', ' days')
}

export const cabinClassOptions = [
  { label: cabinClassLabel('经济舱'), value: '经济舱' as CabinClass },
  { label: cabinClassLabel('头等舱'), value: '头等舱' as CabinClass },
]

export const fareTypeOptions = [
  { label: fareTypeLabel('标准'), value: '标准' as FareType },
  { label: fareTypeLabel('特价'), value: '特价' as FareType },
]

export const instanceStatusOptions = [
  { label: instanceStatusLabel('计划'), value: '计划' as InstanceStatus },
  { label: instanceStatusLabel('可订'), value: '可订' as InstanceStatus },
  { label: instanceStatusLabel('已起飞'), value: '已起飞' as InstanceStatus },
  { label: instanceStatusLabel('已到达'), value: '已到达' as InstanceStatus },
  { label: instanceStatusLabel('已取消'), value: '已取消' as InstanceStatus },
]

export const orderStatusOptions = [
  { label: 'All Statuses', value: '' as const },
  { label: orderStatusLabel('待支付'), value: '待支付' as OrderStatus },
  { label: orderStatusLabel('已支付'), value: '已支付' as OrderStatus },
  { label: orderStatusLabel('已取消'), value: '已取消' as OrderStatus },
  { label: orderStatusLabel('已完成'), value: '已完成' as OrderStatus },
  { label: orderStatusLabel('部分退款'), value: '部分退款' as OrderStatus },
  { label: orderStatusLabel('已完成退款'), value: '已完成退款' as OrderStatus },
]
