import type { SearchFilters } from '@/types/search'

export function normalizeAirlineCodes(filters?: SearchFilters | null): string[] {
  const rawCodes = [
    ...(filters?.airline_codes ?? []),
    filters?.airline_code ?? '',
  ]
  const seen = new Set<string>()
  const codes: string[] = []
  for (const rawCode of rawCodes) {
    const code = String(rawCode).trim().toUpperCase()
    if (!code || seen.has(code)) {
      continue
    }
    seen.add(code)
    codes.push(code)
  }
  return codes
}

export function buildAirlineFilter(codes: string[]): Pick<SearchFilters, 'airline_code' | 'airline_codes'> {
  const normalized = normalizeAirlineCodes({ airline_codes: codes })
  return {
    airline_code: normalized.length === 1 ? normalized[0] : null,
    airline_codes: normalized.length ? normalized : null,
  }
}
