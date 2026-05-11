import { http } from './client'
import type {
  AdminLoginRequest,
  AdminSession,
  AuthSession,
  LoginRequest,
  RegisterRequest,
  RegisterResponse,
  UserSession,
} from '@/types/auth'

export function register(payload: RegisterRequest) {
  return http.post<RegisterResponse>('/auth/register', payload)
}

export function login(payload: LoginRequest) {
  return http.post<UserSession>('/auth/login', payload)
}

export function adminLogin(payload: AdminLoginRequest) {
  return http.post<AdminSession>('/auth/admin-login', payload)
}

export function logout() {
  return http.post<void>('/auth/logout')
}

export function getMe() {
  return http.get<AuthSession>('/auth/me', { silentAuth: true })
}

export const authApi = {
  register,
  login,
  adminLogin,
  logout,
  getMe,
}
