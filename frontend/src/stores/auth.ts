import { defineStore } from 'pinia'
import { authApi } from '@/api/auth'
import type { AdminLoginRequest, AuthSession, LoginRequest, RegisterRequest } from '@/types/auth'

interface AuthState {
  session: AuthSession | null
  loaded: boolean
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    session: null,
    loaded: false,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.session),
    role: (state) => state.session?.role,
    displayName: (state) => state.session?.name ?? '',
    isAdmin: (state) => state.session?.role === 'admin',
  },
  actions: {
    setSession(session: AuthSession | null) {
      this.session = session
      this.loaded = true
    },
    async ensureSession() {
      if (this.loaded) {
        return this.session
      }

      try {
        const session = await authApi.me()
        this.setSession(session)
        return session
      } catch {
        this.setSession(null)
        return null
      }
    },
    async login(payload: LoginRequest) {
      const session = await authApi.login(payload)
      this.setSession(session)
      return session
    },
    async adminLogin(payload: AdminLoginRequest) {
      const session = await authApi.adminLogin(payload)
      this.setSession(session)
      return session
    },
    async register(payload: RegisterRequest) {
      return authApi.register(payload)
    },
    async logout() {
      try {
        await authApi.logout()
      } finally {
        this.setSession(null)
      }
    },
  },
})
