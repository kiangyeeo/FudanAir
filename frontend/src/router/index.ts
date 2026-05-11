import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    requiresAdmin?: boolean
    title?: string
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/layouts/UserLayout.vue'),
    children: [
      { path: '', name: 'home', component: () => import('@/views/public/HomeView.vue'), meta: { title: '航班搜索' } },
      { path: 'search', name: 'search', component: () => import('@/views/user/SearchResultView.vue'), meta: { title: '搜索结果' } },
      { path: 'booking', name: 'booking', component: () => import('@/views/user/BookingView.vue'), meta: { title: '填写订单', requiresAuth: true } },
      { path: 'payment/:orderNo?', name: 'payment', component: () => import('@/views/user/PaymentView.vue'), meta: { title: '支付订单', requiresAuth: true } },
      { path: 'orders', name: 'orders', component: () => import('@/views/user/OrderListView.vue'), meta: { title: '我的订单', requiresAuth: true } },
      { path: 'orders/:orderNo', name: 'order-detail', component: () => import('@/views/user/OrderDetailView.vue'), meta: { title: '订单详情', requiresAuth: true } },
      { path: 'refund', name: 'refund', component: () => import('@/views/user/RefundView.vue'), meta: { title: '退票', requiresAuth: true } },
      { path: 'change', name: 'change', component: () => import('@/views/user/ChangeView.vue'), meta: { title: '改签', requiresAuth: true } },
      { path: 'profile', name: 'profile', component: () => import('@/views/user/ProfileView.vue'), meta: { title: '个人中心', requiresAuth: true } },
    ],
  },
  {
    path: '/',
    component: () => import('@/layouts/BlankLayout.vue'),
    children: [
      { path: 'login', name: 'login', component: () => import('@/views/public/LoginView.vue'), meta: { title: '用户登录' } },
      { path: 'register', name: 'register', component: () => import('@/views/public/RegisterView.vue'), meta: { title: '用户注册' } },
      { path: 'admin/login', name: 'admin-login', component: () => import('@/views/public/AdminLoginView.vue'), meta: { title: '管理员登录' } },
    ],
  },
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAdmin: true },
    children: [
      { path: '', name: 'admin-dashboard', component: () => import('@/views/admin/DashboardView.vue'), meta: { title: '管理概览' } },
      { path: 'cities', name: 'admin-cities', component: () => import('@/views/admin/CityManageView.vue'), meta: { title: '城市管理' } },
      { path: 'airports', name: 'admin-airports', component: () => import('@/views/admin/AirportManageView.vue'), meta: { title: '机场管理' } },
      { path: 'airlines', name: 'admin-airlines', component: () => import('@/views/admin/AirlineManageView.vue'), meta: { title: '航司管理' } },
      { path: 'aircraft', name: 'admin-aircraft', component: () => import('@/views/admin/AircraftManageView.vue'), meta: { title: '机型管理' } },
      { path: 'flights', name: 'admin-flights', component: () => import('@/views/admin/FlightManageView.vue'), meta: { title: '航班管理' } },
      { path: 'instances', name: 'admin-instances', component: () => import('@/views/admin/InstanceManageView.vue'), meta: { title: '实例管理' } },
      { path: 'prices', name: 'admin-prices', component: () => import('@/views/admin/PriceManageView.vue'), meta: { title: '票价管理' } },
      { path: 'orders', name: 'admin-orders', component: () => import('@/views/admin/OrderManageView.vue'), meta: { title: '订单查询' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  const needsAuth = to.matched.some((item) => item.meta.requiresAuth)
  const needsAdmin = to.matched.some((item) => item.meta.requiresAdmin)

  if (!needsAuth && !needsAdmin) {
    return true
  }

  if (!auth.initialized) {
    await auth.init()
  }

  if (!auth.currentUser) {
    return { path: needsAdmin ? '/admin/login' : '/login', query: { redirect: to.fullPath } }
  }

  if (needsAdmin && auth.role !== 'admin') {
    return { path: '/' }
  }

  if (needsAuth && auth.role !== 'user') {
    return { path: '/admin' }
  }

  return true
})

export default router
