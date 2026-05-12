import type { CabinClass, FareType } from './common'
import type { OrderStatus } from './order'
import type { Passenger } from './user'

export type BookingStep = 'select-flight' | 'passengers' | 'confirm' | 'payment' | 'completed'

export interface BookingFlightSelection {
  instance_id: string
  cabin_class: CabinClass
  fare_type: FareType
}

export type BookingSegmentSelection = BookingFlightSelection

export interface BookingRequest {
  instance_id?: string
  cabin_class?: CabinClass
  fare_type?: FareType
  segments?: BookingSegmentSelection[]
  passengers: Passenger[]
}

export interface BookingTicket {
  ticket_no: string
  passenger_id: string
  instance_id: string
  cabin_class: CabinClass
  fare_type: FareType
  actual_price: number
}

export interface BookingSegmentBreakdown {
  instance_id: string
  cabin_class: CabinClass
  fare_type: FareType
  ticket_price_per_seat: number
  fuel_infra_fee_per_seat: number
  actual_price_per_seat: number
  passenger_count: number
  subtotal: number
}

export interface BookingAmountBreakdown {
  ticket_price_per_seat: number
  fuel_infra_fee_per_seat: number
  seat_count: number
  passenger_count: number
  segment_count: number
  segments: BookingSegmentBreakdown[]
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
