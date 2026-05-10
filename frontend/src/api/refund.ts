import { http } from './client'
import type { PageParams, PageResult } from '@/types/common'
import type { ChangeRequest, RefundQuote, RefundQuoteParams, RefundRecord, RefundRequest } from '@/types/refund'

export const refundApi = {
  quote: (params: RefundQuoteParams) => http.get<RefundQuote>('/refund/quote', { params }),
  refund: (payload: RefundRequest) => http.post<RefundRecord>('/refund/refund', payload),
  change: (payload: ChangeRequest) => http.post<RefundRecord>('/refund/change', payload),
  listRecords: (params: PageParams = {}) => http.get<PageResult<RefundRecord>>('/refund/records', { params }),
}
