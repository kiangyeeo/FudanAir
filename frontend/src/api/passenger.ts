import { http, type HttpRequestConfig } from './client'
import type { Passenger, PassengerUpdate } from '@/types/user'

export const passengerApi = {
  list: (config?: HttpRequestConfig) => http.get<Passenger[]>('/passengers', config),
  update: (idNo: string, payload: PassengerUpdate) =>
    http.put<Passenger>(`/passengers/${encodeURIComponent(idNo)}`, payload),
}
