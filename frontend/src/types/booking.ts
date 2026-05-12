import type { CabinClass, FareType } from './common'
import type { OrderStatus } from './order'
import type { Passenger } from './user'

export type BookingStep = 'select-flight' | 'passengers' | 'confirm' | 'payment' | 'completed'

export interface BookingFlightSelection {
  instance_id: string
  cabin_class: CabinClass
  fare_type: FareType
}

export interface BookingRequest extends BookingFlightSelection {
  passengers: Passenger[]
}

export interface BookingTicket {
  ticket_no: string
  passenger_id: string
  actual_price: number
}

export interface BookingAmountBreakdown {
  ticket_price_per_seat: number
  fuel_infra_fee_per_seat: number
  seat_count: number
}

export interface BookingResponse {
  order_no: string
  status: Extract<OrderStatus, '待支付'>
  total_amount: number
  amount_breakdown: BookingAmountBreakdown
  created_at: string
  expires_at: string
  tickets: BookingTicket[]
}

export interface PayResponse {
  order_no: string
  status: Extract<OrderStatus, '已支付'>
  paid_at: string
}
