import type { CabinClass, FareType, PageParams } from './common'

export type InstanceStatus = '计划' | '可订' | '已起飞' | '已到达' | '已取消'

export interface City {
  city_name: string
}

export interface NearAirport {
  iata_code: string
  airport_name: string
  distance: number
}

export interface Airport {
  iata_code: string
  airport_name: string
  city_name: string
}

export interface Airline {
  iata_code: string
  airline_name: string
}

export interface AircraftType {
  model: string
  economy_seats: number
  first_seats: number
}

export interface Flight {
  flight_no: string
  airline_code: string
  airline_name?: string | null
  dep_airport_code: string
  dep_terminal?: string | null
  arr_airport_code: string
  arr_terminal?: string | null
  scheduled_departure: string
  scheduled_arrival: string
  aircraft_model: string
  fuel_infra_fee: number
  weekdays?: number[]
  stopovers?: string[]
}

export interface FlightPayload {
  scheduled_departure: string
  scheduled_arrival: string
  fuel_infra_fee: number
  dep_airport_code: string
  dep_terminal?: string | null
  arr_airport_code: string
  arr_terminal?: string | null
  airline_code: string
  aircraft_model: string
  weekdays: number[]
  stopovers: string[]
}

export interface FlightCreatePayload extends FlightPayload {
  flight_no: string
}

export interface FlightInstance {
  instance_id: string
  flight_no: string
  flight_date: string
  status: InstanceStatus
  economy_left: number
  first_left: number
  scheduled_departure?: string
  scheduled_arrival?: string
  fuel_infra_fee?: number
  adjusted_at?: string | null
  scheduled_departure_adjusted_at?: string | null
  scheduled_arrival_adjusted_at?: string | null
  dep_airport_adjusted_at?: string | null
  arr_airport_adjusted_at?: string | null
  dep_airport_code?: string
  arr_airport_code?: string
  airline_code?: string
  airline_name?: string | null
  cabin_prices?: CabinPrice[]
}

export interface FlightInstanceCreatePayload {
  flight_no: string
  flight_date: string
}

export interface FlightInstanceUpdatePayload {
  scheduled_departure?: string
  scheduled_arrival?: string
  fuel_infra_fee?: number
}
export interface FlightInstanceBatchPayload {
  flight_no: string
  start_date: string
  end_date: string
}

export interface FlightInstanceStatusPayload {
  status: InstanceStatus
}

export interface CabinPrice {
  instance_id: string
  cabin_class: CabinClass
  fare_type: FareType
  price: number
  available_seats: number
}

export interface CabinPricePayload {
  cabin_class: CabinClass
  fare_type: FareType
  price: number
  available_seats: number
}

export interface CabinPriceReplacePayload {
  cabin_prices: CabinPricePayload[]
}

export interface FlightListParams extends PageParams {
  flight_no?: string
  airline_code?: string
  dep_airport_code?: string
  arr_airport_code?: string
}

export interface FlightInstanceListParams extends PageParams {
  flight_no?: string
  flight_date?: string
  status?: string
}
