import type { CabinClass, FareType } from './common'
import type { Passenger } from './user'

export interface OrderListItem {
  order_no: string
  status: string
  total_amount: number
  created_at: string
  ticket_count?: number
}

export interface OrderTicket {
  ticket_no: string
  passenger: Pick<Passenger, 'id_no' | 'real_name'>
  instance_id: string
  flight_no: string
  flight_date: string
  scheduled_departure: string
  dep_airport_code: string
  arr_airport_code: string
  cabin_class: CabinClass
  fare_type: FareType
  actual_price: number
  status: string
}

export interface OrderDetail {
  order_no: string
  user_id: number
  status: string
  total_amount: number
  created_at: string
  tickets: OrderTicket[]
}

export interface OrderQuery {
  page?: number
  page_size?: number
  status?: string
}

export interface AdminOrderQuery extends OrderQuery {
  user_id?: number
  date_from?: string
  date_to?: string
}
