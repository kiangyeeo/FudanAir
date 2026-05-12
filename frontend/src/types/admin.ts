export interface AdminTableColumn {
  prop: string
  label: string
  width?: number
}

export interface AdminStat {
  label: string
  value: string | number
}

export interface AdminDashboardRoute {
  dep_airport_code: string
  arr_airport_code: string
  order_count: number
}

export interface AdminDashboard {
  total_orders: number
  today_orders: number
  total_users: number
  active_users_30d: number
  today_revenue: number
  top_routes: AdminDashboardRoute[]
}
