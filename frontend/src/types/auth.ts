import type { Role } from './common'

export interface UserSession {
  role: 'user'
  user_id: number
  phone: string
  name: string
}

export interface AdminSession {
  role: 'admin'
  admin_id: string
  name: string
}

export type AuthSession = UserSession | AdminSession

export interface RegisterRequest {
  phone: string
  password: string
  name: string
}

export interface LoginRequest {
  phone: string
  password: string
}

export interface AdminLoginRequest {
  admin_id: string
  password: string
}

export interface AuthIdentity {
  role: Role
  name: string
}
