import type { CabinClass, FareType } from './common'
import type { Passenger } from './user'

export type OrderStatus = '待支付' | '已支付' | '已取消' | '已完成' | '部分退款' | '已完成退款'
export type TicketStatus = '有效' | '已退' | '已改签作废' | '已使用'

export interface OrderListItem {
  order_no: string
  user_id: number
  user_name?: string | null
  status: OrderStatus
  total_amount: number
  created_at: string
  ticket_count: number
  active_count: number
  refunded_count: number
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
  status: TicketStatus
}

export interface OrderDetail {
  order_no: string
  user_id: number
  status: OrderStatus
  total_amount: number
  created_at: string
  tickets: OrderTicket[]
}

export interface OrderQuery {
  page?: number
  page_size?: number
  status?: OrderStatus | ''
}

export interface AdminOrderQuery extends OrderQuery {
  user_id?: number
  date_from?: string
  date_to?: string
}
