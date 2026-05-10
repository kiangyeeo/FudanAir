import { http } from './client'
import type { AdminLoginRequest, AdminSession, AuthSession, LoginRequest, RegisterRequest, UserSession } from '@/types/auth'

export const authApi = {
  register: (payload: RegisterRequest) => http.post<UserSession>('/auth/register', payload),
  login: (payload: LoginRequest) => http.post<UserSession>('/auth/login', payload),
  adminLogin: (payload: AdminLoginRequest) => http.post<AdminSession>('/auth/admin-login', payload),
  logout: () => http.post<void>('/auth/logout'),
  me: () => http.get<AuthSession>('/auth/me'),
}
