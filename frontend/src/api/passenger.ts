import { http, type HttpRequestConfig } from './client'
import type { Passenger } from '@/types/user'

export const passengerApi = {
  list: (config?: HttpRequestConfig) => http.get<Passenger[]>('/passengers', config),
  create: (payload: Passenger) => http.post<Passenger>('/passengers', payload),
  update: (idNo: string, payload: Passenger) => http.put<Passenger>(`/passengers/${encodeURIComponent(idNo)}`, payload),
  remove: (idNo: string) => http.delete<void>(`/passengers/${encodeURIComponent(idNo)}`),
}
