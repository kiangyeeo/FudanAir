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

/** 去除机场名末尾的"国际机场"/"机场"后缀，便于紧凑展示；新增机场自动适用 */
export function formatAirportName(name?: string | null) {
  if (!name) {
    return ''
  }
  return name.replace(/(国际)?机场$/, '') || name
}

/** 机场名 + 航站楼，如 "上海虹桥T1"；无航站楼则仅机场名 */
export function withTerminal(name: string, terminal?: string | null) {
  const t = (terminal ?? '').trim()
  return t ? `${name}${t}` : name
}

/** 合并 YYYY-MM-DD 与 HH:MM[:SS] 为本地 Date；任一缺失返回 null */
export function combineDateTime(dateStr?: string | null, timeStr?: string | null): Date | null {
  if (!dateStr || !timeStr) {
    return null
  }
  const dt = new Date(`${dateStr}T${timeStr.slice(0, 8)}`)
  return Number.isNaN(dt.getTime()) ? null : dt
}

/** 距目标时刻的友好倒计时，如 "2天3小时" / "5小时20分" / "即将出发" */
export function formatCountdown(target: Date | null): string {
  if (!target) {
    return '--'
  }
  const diff = target.getTime() - Date.now()
  if (diff <= 0) {
    return '即将出发'
  }
  const totalMinutes = Math.floor(diff / 60000)
  const days = Math.floor(totalMinutes / (60 * 24))
  const hours = Math.floor((totalMinutes % (60 * 24)) / 60)
  const minutes = totalMinutes % 60
  if (days > 0) {
    return `${days}天${hours}小时`
  }
  if (hours > 0) {
    return `${hours}小时${minutes}分`
  }
  return `${minutes}分钟`
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
