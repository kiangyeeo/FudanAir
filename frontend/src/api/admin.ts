import { http } from './client'
import type { AircraftType, Airline, Airport, City, Flight, FlightInstance, NearAirport } from '@/types/flight'

export const adminApi = {
  createCity: (payload: City) => http.post<City>('/cities', payload),
  updateCity: (name: string, payload: City) => http.put<City>(`/cities/${encodeURIComponent(name)}`, payload),
  deleteCity: (name: string) => http.delete<void>(`/cities/${encodeURIComponent(name)}`),
  createNearAirport: (cityName: string, payload: Pick<NearAirport, 'iata_code' | 'distance'>) =>
    http.post<NearAirport>(`/cities/${encodeURIComponent(cityName)}/near-airports`, payload),
  deleteNearAirport: (cityName: string, iata: string) =>
    http.delete<void>(`/cities/${encodeURIComponent(cityName)}/near-airports/${encodeURIComponent(iata)}`),
  createAirport: (payload: Airport) => http.post<Airport>('/airports', payload),
  updateAirport: (iata: string, payload: Omit<Airport, 'iata_code'>) => http.put<Airport>(`/airports/${iata}`, payload),
  deleteAirport: (iata: string) => http.delete<void>(`/airports/${iata}`),
  createAirline: (payload: Airline) => http.post<Airline>('/airlines', payload),
  updateAirline: (iata: string, payload: Pick<Airline, 'airline_name'>) => http.put<Airline>(`/airlines/${iata}`, payload),
  deleteAirline: (iata: string) => http.delete<void>(`/airlines/${iata}`),
  createAircraftType: (payload: AircraftType) => http.post<AircraftType>('/aircraft-types', payload),
  updateAircraftType: (model: string, payload: Omit<AircraftType, 'model'>) =>
    http.put<AircraftType>(`/aircraft-types/${encodeURIComponent(model)}`, payload),
  deleteAircraftType: (model: string) => http.delete<void>(`/aircraft-types/${encodeURIComponent(model)}`),
  createFlight: (payload: Flight) => http.post<Flight>('/flights', payload),
  updateFlight: (flightNo: string, payload: Flight) => http.put<Flight>(`/flights/${flightNo}`, payload),
  deleteFlight: (flightNo: string) => http.delete<void>(`/flights/${flightNo}`),
  createInstance: (payload: Partial<FlightInstance>) => http.post<FlightInstance>('/flight-instances', payload),
  batchGenerateInstances: (payload: unknown) => http.post<void>('/flight-instances/batch-generate', payload),
  updateInstanceStatus: (instanceId: string, payload: { status: string }) => http.patch<FlightInstance>(`/flight-instances/${instanceId}/status`, payload),
  deleteInstance: (instanceId: string) => http.delete<void>(`/flight-instances/${instanceId}`),
  replaceCabinPrices: (instanceId: string, payload: unknown) => http.put<void>(`/flight-instances/${instanceId}/cabin-prices`, payload),
}
