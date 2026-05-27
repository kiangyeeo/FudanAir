import { http, type HttpRequestConfig } from './client'
import type { Passenger, PassengerCreate, PassengerUpdate } from '@/types/user'

export const passengerApi = {
  list: (config?: HttpRequestConfig) => http.get<Passenger[]>('/passengers', config),
  create: (payload: PassengerCreate) => http.post<Passenger>('/passengers', payload),
  update: (idNo: string, payload: PassengerUpdate) =>
    http.put<Passenger>(`/passengers/${encodeURIComponent(idNo)}`, payload),
  delete: (idNo: string) => http.delete<void>(`/passengers/${encodeURIComponent(idNo)}`),
}
