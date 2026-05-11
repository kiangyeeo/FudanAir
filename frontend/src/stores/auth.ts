import { defineStore } from 'pinia'
import { authApi } from '@/api/auth'
import type { AdminLoginRequest, AuthSession, LoginRequest, RegisterRequest } from '@/types/auth'

interface AuthState {
  currentUser: AuthSession | null
  initialized: boolean
  loading: boolean
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    currentUser: null,
    initialized: false,
    loading: false,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.currentUser),
    role: (state) => state.currentUser?.role,
    displayName: (state) => state.currentUser?.name ?? '',
    isAdmin: (state) => state.currentUser?.role === 'admin',
  },
  actions: {
    setCurrentUser(user: AuthSession | null) {
      this.currentUser = user
      this.initialized = true
    },
    async init() {
      if (this.initialized) {
        return this.currentUser
      }

      this.loading = true
      try {
        const user = await authApi.getMe()
        this.setCurrentUser(user)
        return user
      } catch {
        this.setCurrentUser(null)
        return null
      } finally {
        this.loading = false
      }
    },
    async login(payload: LoginRequest) {
      const user = await authApi.login(payload)
      this.setCurrentUser(user)
      return user
    },
    async adminLogin(payload: AdminLoginRequest) {
      const user = await authApi.adminLogin(payload)
      this.setCurrentUser(user)
      return user
    },
    async register(payload: RegisterRequest) {
      return authApi.register(payload)
    },
    async logout() {
      try {
        await authApi.logout()
      } finally {
        this.setCurrentUser(null)
      }
    },
  },
})
