<script setup lang="ts">
import { computed } from 'vue'

type CitySuggestion = {
  value: string
}

const props = withDefaults(defineProps<{
  modelValue: string
  cities: string[]
  placeholder?: string
  disabled?: boolean
  teleported?: boolean
}>(), {
  placeholder: '输入城市名',
  disabled: false,
  teleported: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const value = computed({
  get: () => props.modelValue,
  set: (nextValue: string) => emit('update:modelValue', nextValue),
})

function fetchSuggestions(query: string, done: (items: CitySuggestion[]) => void) {
  const keyword = query.trim()
  if (!keyword) {
    done([])
    return
  }

  done(
    props.cities
      .filter((city) => city.includes(keyword))
      .map((city) => ({ value: city })),
  )
}
</script>

<template>
  <el-autocomplete
    v-model="value"
    :fetch-suggestions="fetchSuggestions"
    :placeholder="placeholder"
    :disabled="disabled"
    :trigger-on-focus="false"
    :teleported="teleported"
    clearable
    class="city-autocomplete"
  />
</template>

<style scoped>
.city-autocomplete {
  width: 100%;
}
</style>
