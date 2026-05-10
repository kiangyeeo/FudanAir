import type { CabinClass, FareType } from './common'
import type { Passenger } from './user'

export interface BookingRequest {
  instance_id: string
  cabin_class: CabinClass
  fare_type: FareType
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
  status: string
  total_amount: number
  amount_breakdown: BookingAmountBreakdown
  created_at: string
  expires_at: string
  tickets: BookingTicket[]
}

export interface PayResponse {
  order_no: string
  status: string
  paid_at: string
}
