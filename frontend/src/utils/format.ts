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

/** 计算两个 HH:MM[:SS] 时刻之间的分钟差，跨天则按次日计算 */
export function minutesBetween(start?: string | null, end?: string | null): number | null {
  if (!start || !end) {
    return null
  }
  const toMinutes = (value: string) => {
    const [h, m] = value.split(':').map(Number)
    if (Number.isNaN(h) || Number.isNaN(m)) {
      return null
    }
    return h * 60 + m
  }
  const startMin = toMinutes(start)
  const endMin = toMinutes(end)
  if (startMin === null || endMin === null) {
    return null
  }
  const diff = endMin - startMin
  return diff >= 0 ? diff : diff + 24 * 60
}
