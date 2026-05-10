import { http } from './client'
import type { PageResult } from '@/types/common'
import type {
  Airline,
  Airport,
  CabinPrice,
  City,
  Flight,
  FlightInstance,
  FlightInstanceListParams,
  FlightListParams,
  NearAirport,
} from '@/types/flight'

export const flightApi = {
  listCities: () => http.get<City[]>('/cities'),
  listNearAirports: (cityName: string) => http.get<NearAirport[]>(`/cities/${encodeURIComponent(cityName)}/near-airports`),
  listAirports: () => http.get<Airport[]>('/airports'),
  getAirport: (iata: string) => http.get<Airport>(`/airports/${iata}`),
  listAirlines: () => http.get<Airline[]>('/airlines'),
  listFlights: (params: FlightListParams = {}) => http.get<PageResult<Flight>>('/flights', { params }),
  getFlight: (flightNo: string) => http.get<Flight>(`/flights/${flightNo}`),
  listInstances: (params: FlightInstanceListParams = {}) => http.get<PageResult<FlightInstance>>('/flight-instances', { params }),
  getInstance: (instanceId: string) => http.get<FlightInstance>(`/flight-instances/${instanceId}`),
  listCabinPrices: (instanceId: string) => http.get<CabinPrice[]>(`/flight-instances/${instanceId}/cabin-prices`),
}
