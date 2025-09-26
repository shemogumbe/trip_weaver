export interface TripRequest {
  origin: string;
  destination: string;
  start_date: string;
  end_date: string;
  hobbies: string[];
  adults: number;
  budget_level: 'low' | 'mid' | 'high';
  trip_type: string;
  constraints: Record<string, string>;
}

export interface Flight {
  summary: string;
  depart_time?: string;
  arrive_time?: string;
  airline?: string;
  stops?: number;
  est_price?: number;
  currency?: string;
  booking_links?: string[];
}

export interface Stay {
  name: string;
  area: string;
  est_price_per_night?: number;
  currency?: string;
  score?: number;
  highlights?: string[];
  booking_links?: string[];
}

export interface Activity {
  title: string;
  location: string;
  duration_hours?: number;
  est_price?: number;
  currency?: string;
  source_url?: string;
  tags?: string[];
}

export interface DayPlan {
  date: string;
  morning?: Activity;
  afternoon?: Activity;
  evening?: Activity;
}

export interface TripPlan {
  flights: Flight[];
  stays: Stay[];
  activities: DayPlan[];
}

export interface ProcessingLog {
  stage: string;
  raw_count: number;
  refined_count: number;
  error?: string;
  message?: string;
}

export interface TripResponse {
  plan: TripPlan;
  logs: ProcessingLog[];
  success: boolean;
  message: string;
}

export interface AppState {
  isLoading: boolean;
  tripPlan: TripPlan | null;
  logs: ProcessingLog[];
  error: string | null;
  lastSearch: TripRequest | null;
}
