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
  fee: number
  refund_amount?: number
  price_diff?: number
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

export interface RefundRecord {
  id: number
  ticket_no: string
  op_type: string
  fee: number
  created_at: string
  new_ticket_no?: string | null
}
