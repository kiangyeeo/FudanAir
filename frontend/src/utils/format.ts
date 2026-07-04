export function formatCurrency(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '¥--'
  }
  return `¥${value.toFixed(2)}`
}

function pad2(n: number) {
  return n < 10 ? `0${n}` : `${n}`
}

function formatLocalDateTime(d: Date) {
  return (
    `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ` +
    `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`
  )
}

/**
 * 友好展示日期/时间：
 * - 纯日期（2026-05-25）原样返回
 * - 含时区标识（Z / ±HH:MM）按本地时区格式化，避免直接展示 UTC
 * - 朴素本地时间仅做展示清洗：去掉 T 分隔符与毫秒
 */
export function formatDate(value?: string | null) {
  if (!value) {
    return '--'
  }
  if (!value.includes('T') && !value.includes(' ')) {
    return value
  }
  if (/[zZ]$/.test(value) || /[+-]\d{2}:\d{2}$/.test(value)) {
    const d = new Date(value)
    if (!Number.isNaN(d.getTime())) {
      return formatLocalDateTime(d)
    }
  }
  return value.replace('T', ' ').replace(/\.\d+.*$/, '').slice(0, 19)
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
  if (hours <= 0) {
    return `${rest} min`
  }
  return rest > 0 ? `${hours}h ${rest}m` : `${hours}h`
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

/** YYYY-MM-DD -> "2026年7月8日"（去前导零）；非该格式原样返回 */
export function formatChineseDate(value?: string | null) {
  if (!value) {
    return '--'
  }
  const matched = /^(\d{4})-(\d{1,2})-(\d{1,2})/.exec(value)
  if (!matched) {
    return value
  }
  return new Date(`${matched[1]}-${matched[2].padStart(2, '0')}-${matched[3].padStart(2, '0')}T00:00:00`)
    .toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

/** 证件号脱敏：保留前 4 位与后 4 位，中间打码（不足 8 位时仅露首尾各 1 位） */
export function maskIdNo(idNo?: string | null) {
  if (!idNo) {
    return '--'
  }
  const value = String(idNo).trim()
  if (value.length <= 2) {
    return value
  }
  if (value.length < 8) {
    return `${value[0]}${'*'.repeat(value.length - 2)}${value[value.length - 1]}`
  }
  return `${value.slice(0, 4)}${'*'.repeat(value.length - 8)}${value.slice(-4)}`
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
    return 'Departing soon'
  }
  const totalMinutes = Math.floor(diff / 60000)
  const days = Math.floor(totalMinutes / (60 * 24))
  const hours = Math.floor((totalMinutes % (60 * 24)) / 60)
  const minutes = totalMinutes % 60
  if (days > 0) {
    return hours > 0 ? `${days}d ${hours}h` : `${days}d`
  }
  if (hours > 0) {
    return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`
  }
  return `${minutes}m`
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
