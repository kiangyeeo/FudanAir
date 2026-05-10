export type Role = 'user' | 'admin'
export type CabinClass = '经济舱' | '头等舱'
export type FareType = '标准' | '特价' | string
export type SortOrder = 'asc' | 'desc'

export interface PageParams {
  page?: number
  page_size?: number
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface ApiErrorResponse {
  code: string
  message: string
}
