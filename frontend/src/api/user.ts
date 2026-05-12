import { http } from './client'
import type { PasswordUpdate, UserProfile, UserProfileUpdate } from '@/types/user'

export const userApi = {
  getProfile: () => http.get<UserProfile>('/users/me'),
  updateProfile: (payload: UserProfileUpdate) => http.patch<UserProfile>('/users/me', payload),
  updatePassword: (payload: PasswordUpdate) => http.post<void>('/users/me/password', payload),
}
