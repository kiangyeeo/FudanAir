import { http } from './client'
import type { Passenger, PasswordUpdate, UserProfile, UserProfileUpdate } from '@/types/user'

export const userApi = {
  getProfile: () => http.get<UserProfile>('/users/me'),
  updateProfile: (payload: UserProfileUpdate) => http.patch<UserProfile>('/users/me', payload),
  updatePassword: (payload: PasswordUpdate) => http.post<void>('/users/me/password', payload),
  listPassengers: () => http.get<Passenger[]>('/passengers'),
  createPassenger: (payload: Passenger) => http.post<Passenger>('/passengers', payload),
  updatePassenger: (idNo: string, payload: Passenger) => http.put<Passenger>(`/passengers/${encodeURIComponent(idNo)}`, payload),
  deletePassenger: (idNo: string) => http.delete<void>(`/passengers/${encodeURIComponent(idNo)}`),
}
