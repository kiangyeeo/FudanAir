import { http } from './client'
import type { AdminDashboard } from '@/types/admin'
import type {
  AircraftType,
  Airline,
  Airport,
  CabinPrice,
  CabinPriceReplacePayload,
  City,
  Flight,
  FlightCreatePayload,
  FlightInstance,
  FlightInstanceBatchPayload,
  FlightInstanceCreatePayload,
  FlightInstanceStatusPayload,
  FlightPayload,
  NearAirport,
} from '@/types/flight'

export const adminApi = {
  getDashboard: () => http.get<AdminDashboard>('/admin/dashboard'),
  createCity: (payload: City) => http.post<City>('/cities', payload),
  updateCity: (name: string, payload: City) => http.put<City>(`/cities/${encodeURIComponent(name)}`, payload),
  deleteCity: (name: string) => http.delete<void>(`/cities/${encodeURIComponent(name)}`),
  createNearAirport: (cityName: string, payload: Pick<NearAirport, 'iata_code' | 'distance'>) =>
    http.post<NearAirport>(`/cities/${encodeURIComponent(cityName)}/near-airports`, payload),
  deleteNearAirport: (cityName: string, iata: string) =>
    http.delete<void>(`/cities/${encodeURIComponent(cityName)}/near-airports/${encodeURIComponent(iata)}`),
  createAirport: (payload: Airport) => http.post<Airport>('/airports', payload),
  updateAirport: (iata: string, payload: Airport) => http.put<Airport>(`/airports/${iata}`, payload),
  deleteAirport: (iata: string) => http.delete<void>(`/airports/${iata}`),
  createAirline: (payload: Airline) => http.post<Airline>('/airlines', payload),
  updateAirline: (iata: string, payload: Airline) => http.put<Airline>(`/airlines/${iata}`, payload),
  deleteAirline: (iata: string) => http.delete<void>(`/airlines/${iata}`),
  createAircraftType: (payload: AircraftType) => http.post<AircraftType>('/aircraft-types', payload),
  updateAircraftType: (model: string, payload: Omit<AircraftType, 'model'>) =>
    http.put<AircraftType>(`/aircraft-types/${encodeURIComponent(model)}`, payload),
  deleteAircraftType: (model: string) => http.delete<void>(`/aircraft-types/${encodeURIComponent(model)}`),
  createFlight: (payload: FlightCreatePayload) => http.post<Flight>('/flights', payload),
  updateFlight: (flightNo: string, payload: FlightPayload) =>
    http.put<Flight>(`/flights/${encodeURIComponent(flightNo)}`, payload),
  deleteFlight: (flightNo: string) => http.delete<void>(`/flights/${encodeURIComponent(flightNo)}`),
  createInstance: (payload: FlightInstanceCreatePayload) => http.post<FlightInstance>('/flight-instances', payload),
  batchGenerateInstances: (payload: FlightInstanceBatchPayload) =>
    http.post<FlightInstance[]>('/flight-instances/batch-generate', payload),
  updateInstanceStatus: (instanceId: string, payload: FlightInstanceStatusPayload) =>
    http.patch<FlightInstance>(`/flight-instances/${encodeURIComponent(instanceId)}/status`, payload),
  deleteInstance: (instanceId: string) => http.delete<void>(`/flight-instances/${encodeURIComponent(instanceId)}`),
  replaceCabinPrices: (instanceId: string, payload: CabinPriceReplacePayload) =>
    http.put<CabinPrice[]>(`/flight-instances/${encodeURIComponent(instanceId)}/cabin-prices`, payload),
}
