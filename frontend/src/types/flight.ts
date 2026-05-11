import type { CabinClass, FareType, PageParams } from './common'

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
  dep_airport_code: string
  arr_airport_code: string
  scheduled_departure: string
  scheduled_arrival: string
  aircraft_model: string
  fuel_infra_fee: number
}

export interface FlightInstance {
  instance_id: string
  flight_no: string
  flight_date: string
  status: string
  economy_left: number
  first_left: number
}

export interface CabinPrice {
  instance_id: string
  cabin_class: CabinClass
  fare_type: FareType
  price: number
  available_seats: number
}

export interface FlightListParams extends PageParams {
  airline_code?: string
  dep_airport_code?: string
  arr_airport_code?: string
}

export interface FlightInstanceListParams extends PageParams {
  flight_no?: string
  flight_date?: string
  status?: string
}
