export function isPhone(value: string) {
  return /^1[3-9]\d{9}$/.test(value)
}

export function isPassword(value: string) {
  return value.length >= 6 && value.length <= 32
}

export function isIdNo(value: string) {
  return /^\d{17}[\dXx]$/.test(value)
}
