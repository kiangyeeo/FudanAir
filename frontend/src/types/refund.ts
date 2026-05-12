import type { CabinClass, FareType } from './common'

export interface RefundQuoteParams {
  ticket_no: string
  op_type: 'refund' | 'change'
  new_instance_id?: string
  new_cabin_class?: CabinClass
  new_fare_type?: FareType
}

export interface RefundQuote {
  ticket_no: string
  op_type: 'refund' | 'change'
  actual_price?: number
  old_actual_price?: number
  new_actual_price?: number
  fee_rate: number
  fee: number
  refund_amount?: number
  price_diff?: number
  amount_user_pays?: number
  tier: string
}

export interface RefundRequest {
  ticket_no: string
}

export interface ChangeRequest {
  ticket_no: string
  new_instance_id: string
  new_cabin_class: CabinClass
  new_fare_type: FareType
}

export interface RefundTicketResponse {
  refund_id: number
  ticket_no: string
  fee: number
  refund_amount: number
  ticket_status: '已退'
  order_status: '部分退款' | '已完成退款'
}

export interface ChangeTicketResponse {
  refund_id: number
  old_ticket_no: string
  new_ticket_no: string
  fee: number
  price_diff: number
  amount_user_pays: number
  old_ticket_status: '已改签作废'
  new_ticket_status: '有效'
}

export interface RefundRecord {
  refund_id: number
  ticket_no: string
  op_type: string
  fee: number
  price_diff: number
  op_time: string
  new_ticket_no?: string | null
}
