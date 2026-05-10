import { http } from './client'
import type { PageResult } from '@/types/common'
import type { AdminOrderQuery, OrderDetail, OrderListItem, OrderQuery } from '@/types/order'

export const orderApi = {
  listMine: (params: OrderQuery = {}) => http.get<PageResult<OrderListItem>>('/orders', { params }),
  getDetail: (orderNo: string) => http.get<OrderDetail>(`/orders/${orderNo}`),
  listAdmin: (params: AdminOrderQuery = {}) => http.get<PageResult<OrderListItem>>('/admin/orders', { params }),
}
