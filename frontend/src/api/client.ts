import axios, { type AxiosError, type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiErrorResponse } from '@/types/common'

export interface HttpClient {
  get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T>
  post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
  put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
  patch<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
  delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T>
}

const client = axios.create({
  baseURL: '/api',
  timeout: 10000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json; charset=utf-8',
  },
})

client.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError<ApiErrorResponse>) => {
    const status = error.response?.status
    const data = error.response?.data

    if (status === 401) {
      void import('@/router').then(({ default: router }) => {
        const current = router.currentRoute.value
        const loginPath = current.path.startsWith('/admin') ? '/admin/login' : '/login'

        if (current.path !== '/login' && current.path !== '/admin/login') {
          router.push({ path: loginPath, query: { redirect: current.fullPath } })
        }
      })
    } else if (status === 403) {
      ElMessage.error(data?.message || '无权限')
    } else if (status && status >= 400 && status < 500) {
      ElMessage.error(data?.message || '请求参数有误')
    } else {
      ElMessage.error('系统繁忙,请稍后重试')
    }

    return Promise.reject(error)
  },
)

export const http = client as unknown as HttpClient
