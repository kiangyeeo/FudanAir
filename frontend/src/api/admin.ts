import { http } from './client'
import type { Airline, Airport, City, Flight, FlightInstance } from '@/types/flight'

export const adminApi = {
  createCity: (payload: City) => http.post<City>('/cities', payload),
  deleteCity: (name: string) => http.delete<void>(`/cities/${encodeURIComponent(name)}`),
  createAirport: (payload: Airport) => http.post<Airport>('/airports', payload),
  updateAirport: (iata: string, payload: Airport) => http.put<Airport>(`/airports/${iata}`, payload),
  deleteAirport: (iata: string) => http.delete<void>(`/airports/${iata}`),
  createAirline: (payload: Airline) => http.post<Airline>('/airlines', payload),
  updateAirline: (iata: string, payload: Pick<Airline, 'airline_name'>) => http.put<Airline>(`/airlines/${iata}`, payload),
  deleteAirline: (iata: string) => http.delete<void>(`/airlines/${iata}`),
  createFlight: (payload: Flight) => http.post<Flight>('/flights', payload),
  updateFlight: (flightNo: string, payload: Flight) => http.put<Flight>(`/flights/${flightNo}`, payload),
  deleteFlight: (flightNo: string) => http.delete<void>(`/flights/${flightNo}`),
  createInstance: (payload: Partial<FlightInstance>) => http.post<FlightInstance>('/flight-instances', payload),
  batchGenerateInstances: (payload: unknown) => http.post<void>('/flight-instances/batch-generate', payload),
  updateInstanceStatus: (instanceId: string, payload: { status: string }) => http.patch<FlightInstance>(`/flight-instances/${instanceId}/status`, payload),
  deleteInstance: (instanceId: string) => http.delete<void>(`/flight-instances/${instanceId}`),
  replaceCabinPrices: (instanceId: string, payload: unknown) => http.put<void>(`/flight-instances/${instanceId}/cabin-prices`, payload),
}
