import { http } from './client'
import type { FlightSearchRequest, FlightSearchResponse, TransitCandidate } from '@/types/search'

export const searchApi = {
  searchFlights: (payload: FlightSearchRequest) => http.post<FlightSearchResponse>('/search/flights', payload),
  searchTransit: (payload: FlightSearchRequest) => http.post<TransitCandidate[]>('/search/transit', payload),
}
