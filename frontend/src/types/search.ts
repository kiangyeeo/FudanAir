import type { CabinClass, FareType, SortOrder } from './common'

export interface SearchFilters {
  airline_code?: string | null
  airline_codes?: string[] | null
  cabin_class?: CabinClass | null
  departure_time_range?: [string, string] | null
  price_min?: number | null
  price_max?: number | null
  include_stopover?: boolean
  include_transit?: boolean
  include_nearby?: boolean
}

export interface SearchSort {
  field: 'price' | 'duration' | 'departure'
  order: SortOrder
}

export interface FlightSearchRequest {
  dep_city: string
  arr_city: string
  flight_date: string
  filters?: SearchFilters
  sort?: SearchSort
}

export interface DirectFlightCandidate {
  type: 'direct'
  instance_id: string
  flight_no: string
  dep_airport_code: string
  arr_airport_code: string
  scheduled_departure: string
  scheduled_arrival: string
  airline_code: string
  airline_name: string
  aircraft_model: string
  min_price: number
  min_ticket_price: number
  min_cabin_class: CabinClass
  min_fare_type: FareType
  fuel_infra_fee: number
  economy_left: number
  first_left: number
}

export interface TransitCandidate {
  type: 'transit'
  leg1: DirectFlightCandidate
  leg2: DirectFlightCandidate
  transit_airport: string
  transit_minutes: number
  total_duration_minutes: number
  total_min_price: number
  total_ticket_price: number
  total_fuel_infra_fee: number
}

export interface NearbyFlightCandidate extends Omit<DirectFlightCandidate, 'type'> {
  type: 'nearby'
  replacement: 'departure' | 'arrival'
  replaced_airport: string
  actual_dep_city?: string
  actual_arr_city?: string
  /** 该临近机场到所搜索城市的距离（公里） */
  nearby_distance: number
}

export interface FlightSearchResponse {
  direct: DirectFlightCandidate[]
  transit: TransitCandidate[]
  nearby: NearbyFlightCandidate[]
}
