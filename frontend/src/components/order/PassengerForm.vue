<script setup lang="ts">
import type { Passenger } from '@/types/user'

const props = defineProps<{
  modelValue: Passenger[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: Passenger[]]
}>()

function update(index: number, key: keyof Passenger, value: string) {
  const next = props.modelValue.map((item, itemIndex) => (itemIndex === index ? { ...item, [key]: value } : item))
  emit('update:modelValue', next)
}

function addPassenger() {
  emit('update:modelValue', [...props.modelValue, { id_no: '', real_name: '', birth_date: '' }])
}

function removePassenger(index: number) {
  emit('update:modelValue', props.modelValue.filter((_, itemIndex) => itemIndex !== index))
}
</script>

<template>
  <div class="passenger-form">
    <div class="toolbar">
      <el-button type="primary" @click="addPassenger">新增乘机人</el-button>
    </div>
    <el-table :data="modelValue" border>
      <el-table-column label="证件号" min-width="210">
        <template #default="{ row, $index }">
          <el-input :model-value="row.id_no" @update:model-value="update($index, 'id_no', String($event))" />
        </template>
      </el-table-column>
      <el-table-column label="姓名" min-width="140">
        <template #default="{ row, $index }">
          <el-input :model-value="row.real_name" @update:model-value="update($index, 'real_name', String($event))" />
        </template>
      </el-table-column>
      <el-table-column label="出生日期" min-width="160">
        <template #default="{ row, $index }">
          <el-date-picker :model-value="row.birth_date" type="date" value-format="YYYY-MM-DD" @update:model-value="update($index, 'birth_date', String($event))" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="90">
        <template #default="{ $index }">
          <el-button link type="danger" @click="removePassenger($index)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.passenger-form {
  display: grid;
  gap: 10px;
}
</style>
