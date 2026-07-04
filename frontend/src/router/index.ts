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
      { path: '', name: 'home', component: () => import('@/views/public/HomeView.vue'), meta: { title: 'Flight Search' } },
      { path: 'search', name: 'search', component: () => import('@/views/user/SearchResultView.vue'), meta: { title: 'Search Results' } },
      { path: 'trips', name: 'trips', component: () => import('@/views/user/UpcomingView.vue'), meta: { title: 'My Tickets', requiresAuth: true } },
      { path: 'booking', name: 'booking', component: () => import('@/views/user/BookingView.vue'), meta: { title: 'Create Order', requiresAuth: true } },
      { path: 'payment/:orderNo?', name: 'payment', component: () => import('@/views/user/PaymentView.vue'), meta: { title: 'Payment', requiresAuth: true } },
      { path: 'orders', name: 'orders', component: () => import('@/views/user/OrderListView.vue'), meta: { title: 'My Orders', requiresAuth: true } },
      { path: 'orders/:orderNo', name: 'order-detail', component: () => import('@/views/user/OrderDetailView.vue'), meta: { title: 'Order Details', requiresAuth: true } },
      { path: 'refund', name: 'refund', component: () => import('@/views/user/RefundView.vue'), meta: { title: 'Refund', requiresAuth: true } },
      { path: 'change', name: 'change', component: () => import('@/views/user/ChangeView.vue'), meta: { title: 'Change Flight', requiresAuth: true } },
      { path: 'profile', name: 'profile', component: () => import('@/views/user/ProfileView.vue'), meta: { title: 'Profile', requiresAuth: true } },
    ],
  },
  {
    path: '/',
    component: () => import('@/layouts/BlankLayout.vue'),
    children: [
      { path: 'login', name: 'login', component: () => import('@/views/public/LoginView.vue'), meta: { title: 'User Login' } },
      { path: 'register', name: 'register', component: () => import('@/views/public/RegisterView.vue'), meta: { title: 'User Registration' } },
      { path: 'admin/login', name: 'admin-login', component: () => import('@/views/public/AdminLoginView.vue'), meta: { title: 'Admin Login' } },
    ],
  },
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAdmin: true },
    children: [
      { path: '', name: 'admin-dashboard', component: () => import('@/views/admin/DashboardView.vue'), meta: { title: 'Dashboard' } },
      { path: 'cities', name: 'admin-cities', component: () => import('@/views/admin/CityManageView.vue'), meta: { title: 'Cities' } },
      { path: 'airports', name: 'admin-airports', component: () => import('@/views/admin/AirportManageView.vue'), meta: { title: 'Airports' } },
      { path: 'airlines', name: 'admin-airlines', component: () => import('@/views/admin/AirlineManageView.vue'), meta: { title: 'Airlines' } },
      { path: 'aircraft', name: 'admin-aircraft', component: () => import('@/views/admin/AircraftManageView.vue'), meta: { title: 'Aircraft Types' } },
      { path: 'flights', name: 'admin-flights', component: () => import('@/views/admin/FlightManageView.vue'), meta: { title: 'Flights' } },
      { path: 'instances', name: 'admin-instances', component: () => import('@/views/admin/InstanceManageView.vue'), meta: { title: 'Flight Instances' } },
      { path: 'prices', name: 'admin-prices', component: () => import('@/views/admin/PriceManageView.vue'), meta: { title: 'Pricing' } },
      { path: 'orders', name: 'admin-orders', component: () => import('@/views/admin/OrderManageView.vue'), meta: { title: 'Orders' } },
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
