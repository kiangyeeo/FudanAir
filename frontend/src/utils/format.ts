export function formatCurrency(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '¥--'
  }
  return `¥${value.toFixed(2)}`
}

export function formatDate(value?: string | null) {
  if (!value) {
    return '--'
  }
  return value
}

export function formatTime(value?: string | null) {
  if (!value) {
    return '--:--'
  }
  return value.slice(0, 5)
}

export function formatDuration(minutes?: number | null) {
  if (minutes === null || minutes === undefined) {
    return '--'
  }
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return `${hours}小时${rest}分`
}
