<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Check, Close, Edit, Lock, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { passengerApi } from '@/api/passenger'
import { userApi } from '@/api/user'
import { useAuthStore } from '@/stores/auth'
import type { Passenger, PassengerUpdate, UserProfile, UserProfileUpdate } from '@/types/user'
import { isPassword, isPhone } from '@/utils/validators'

type PasswordForm = {
  old_password: string
  new_password: string
  confirm_password: string
}

const auth = useAuthStore()
const activeTab = ref('profile')
const profile = ref<UserProfile | null>(null)
const passengers = ref<Passenger[]>([])
const profileLoading = ref(false)
const passengerLoading = ref(false)
const profileSaving = ref(false)
const passwordSaving = ref(false)
const passengerSaving = ref(false)
const editingId = ref('')

const profileForm = reactive<UserProfileUpdate>({
  name: '',
  phone: '',
})
const passwordForm = reactive<PasswordForm>({
  old_password: '',
  new_password: '',
  confirm_password: '',
})
const editForm = reactive<PassengerUpdate>({
  real_name: '',
  birth_date: '',
})

const profileChanged = computed(() => {
  if (!profile.value) {
    return false
  }
  return profileForm.name?.trim() !== profile.value.name || profileForm.phone?.trim() !== profile.value.phone
})

async function loadProfile() {
  profileLoading.value = true
  try {
    const data = await userApi.getProfile()
    profile.value = data
    profileForm.name = data.name
    profileForm.phone = data.phone
  } finally {
    profileLoading.value = false
  }
}

async function saveProfile() {
  const payload = normalizeProfile()
  if (!payload) {
    return
  }

  profileSaving.value = true
  try {
    const data = await userApi.updateProfile(payload)
    profile.value = data
    profileForm.name = data.name
    profileForm.phone = data.phone
    if (auth.currentUser?.role === 'user') {
      auth.setCurrentUser({ ...auth.currentUser, name: data.name, phone: data.phone })
    }
    ElMessage.success('个人信息已更新')
  } finally {
    profileSaving.value = false
  }
}

async function savePassword() {
  const oldPassword = passwordForm.old_password.trim()
  const newPassword = passwordForm.new_password.trim()
  const confirmPassword = passwordForm.confirm_password.trim()
  if (!oldPassword) {
    ElMessage.warning('请输入原密码')
    return
  }
  if (!isPassword(newPassword)) {
    ElMessage.warning('新密码长度需为 6-32 位')
    return
  }
  if (newPassword !== confirmPassword) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }

  passwordSaving.value = true
  try {
    await userApi.updatePassword({
      old_password: oldPassword,
      new_password: newPassword,
    })
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
    ElMessage.success('密码已更新')
  } finally {
    passwordSaving.value = false
  }
}

async function loadPassengers() {
  passengerLoading.value = true
  try {
    passengers.value = await passengerApi.list()
  } finally {
    passengerLoading.value = false
  }
}

function startEdit(row: Passenger) {
  editingId.value = row.id_no
  editForm.real_name = row.real_name
  editForm.birth_date = row.birth_date
}

function cancelEdit() {
  editingId.value = ''
  editForm.real_name = ''
  editForm.birth_date = ''
}

async function savePassenger(row: Passenger) {
  const payload = normalizePassenger()
  if (!payload) {
    return
  }

  passengerSaving.value = true
  try {
    const saved = await passengerApi.update(row.id_no, payload)
    passengers.value = passengers.value.map((item) => (item.id_no === saved.id_no ? saved : item))
    cancelEdit()
    ElMessage.success('乘机人信息已更新')
  } finally {
    passengerSaving.value = false
  }
}

function normalizeProfile(): UserProfileUpdate | null {
  const name = profileForm.name?.trim() ?? ''
  const phone = profileForm.phone?.trim() ?? ''
  if (!name) {
    ElMessage.warning('请输入姓名')
    return null
  }
  if (!isPhone(phone)) {
    ElMessage.warning('手机号格式错误')
    return null
  }
  return { name, phone }
}

function normalizePassenger(): PassengerUpdate | null {
  const realName = editForm.real_name.trim()
  if (!realName || !editForm.birth_date) {
    ElMessage.warning('请完整填写乘机人姓名和出生日期')
    return null
  }
  return {
    real_name: realName,
    birth_date: editForm.birth_date,
  }
}

onMounted(() => {
  void loadProfile()
  void loadPassengers()
})
</script>

<template>
  <div class="page-shell profile-page">
    <section class="page-section">
      <h1 class="page-title">个人中心</h1>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="个人信息" name="profile">
          <div v-loading="profileLoading" class="tab-panel">
            <el-form :model="profileForm" label-position="top" class="profile-form">
              <div class="form-grid">
                <el-form-item label="用户 ID">
                  <el-input :model-value="profile?.user_id ?? ''" disabled />
                </el-form-item>
                <el-form-item label="姓名">
                  <el-input v-model="profileForm.name" maxlength="64" />
                </el-form-item>
                <el-form-item label="手机号">
                  <el-input v-model="profileForm.phone" maxlength="20" />
                </el-form-item>
              </div>
              <div class="actions">
                <el-button
                  type="primary"
                  :icon="Check"
                  :disabled="!profileChanged"
                  :loading="profileSaving"
                  @click="saveProfile"
                >
                  保存资料
                </el-button>
                <el-button :icon="Refresh" @click="loadProfile">刷新</el-button>
              </div>
            </el-form>

            <el-divider />

            <h2>修改密码</h2>
            <el-form :model="passwordForm" label-position="top" class="password-form">
              <div class="form-grid">
                <el-form-item label="原密码">
                  <el-input v-model="passwordForm.old_password" type="password" show-password maxlength="32" />
                </el-form-item>
                <el-form-item label="新密码">
                  <el-input v-model="passwordForm.new_password" type="password" show-password maxlength="32" />
                </el-form-item>
                <el-form-item label="确认新密码">
                  <el-input v-model="passwordForm.confirm_password" type="password" show-password maxlength="32" />
                </el-form-item>
              </div>
              <div class="actions">
                <el-button type="primary" :icon="Lock" :loading="passwordSaving" @click="savePassword">
                  修改密码
                </el-button>
              </div>
            </el-form>
          </div>
        </el-tab-pane>

        <el-tab-pane label="乘机人信息管理" name="passengers">
          <div class="tab-panel">
            <div class="table-toolbar">
              <h2>乘机人</h2>
              <el-button :icon="Refresh" :loading="passengerLoading" @click="loadPassengers">刷新</el-button>
            </div>
            <el-table
              v-loading="passengerLoading"
              :data="passengers"
              border
              row-key="id_no"
              empty-text="暂无历史乘机人"
            >
              <el-table-column prop="id_no" label="证件号" min-width="210" />
              <el-table-column label="姓名" min-width="160">
                <template #default="{ row }">
                  <el-input v-if="editingId === row.id_no" v-model="editForm.real_name" maxlength="64" />
                  <span v-else>{{ row.real_name }}</span>
                </template>
              </el-table-column>
              <el-table-column label="出生日期" min-width="180">
                <template #default="{ row }">
                  <el-date-picker
                    v-if="editingId === row.id_no"
                    v-model="editForm.birth_date"
                    type="date"
                    value-format="YYYY-MM-DD"
                  />
                  <span v-else>{{ row.birth_date }}</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="150" fixed="right">
                <template #default="{ row }">
                  <template v-if="editingId === row.id_no">
                    <el-button link type="primary" :icon="Check" :loading="passengerSaving" @click="savePassenger(row)">
                      保存
                    </el-button>
                    <el-button link :icon="Close" :disabled="passengerSaving" @click="cancelEdit">取消</el-button>
                  </template>
                  <el-button
                    v-else
                    link
                    type="primary"
                    :icon="Edit"
                    :disabled="Boolean(editingId)"
                    @click="startEdit(row)"
                  >
                    编辑
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </section>
  </div>
</template>

<style scoped lang="scss">
.profile-page {
  display: grid;
  gap: 16px;
}

.tab-panel {
  padding-top: 4px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.actions,
.table-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.actions {
  margin-top: 4px;
}

.table-toolbar {
  justify-content: space-between;
  margin-bottom: 12px;
}

h2 {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 600;
}

@media (max-width: 760px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
