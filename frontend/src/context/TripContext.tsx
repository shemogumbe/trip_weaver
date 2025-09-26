import React, { createContext, useContext, useReducer, ReactNode } from 'react';
import { AppState, TripRequest, TripResponse } from '../types';
import { tripReducer } from '../reducers/tripReducer';
import { TripAction } from '../reducers/tripReducer';
import { apiUrl } from '../utils/api';

interface TripContextType {
  state: AppState;
  searchTrip: (request: TripRequest) => Promise<void>;
  clearResults: () => void;
}

const TripContext = createContext<TripContextType | undefined>(undefined);

const initialState: AppState = {
  isLoading: false,
  tripPlan: null,
  logs: [],
  error: null,
  lastSearch: null,
};

interface TripProviderProps {
  children: ReactNode;
}

export const TripProvider: React.FC<TripProviderProps> = ({ children }) => {
  const [state, dispatch] = useReducer(tripReducer, initialState);

  const searchTrip = async (request: TripRequest) => {
    dispatch({ type: 'SEARCH_START', payload: request });
    
    try {
      const useStreaming = true;

      if (useStreaming && typeof window !== 'undefined' && 'EventSource' in window) {
        // Establish SSE connection: send payload via query (simple approach)
        const params = new URLSearchParams({
          origin: request.origin,
          destination: request.destination,
          start_date: request.start_date,
          end_date: request.end_date,
          adults: String(request.adults),
          budget_level: request.budget_level,
          trip_type: request.trip_type,
          // serialize hobbies and constraints as JSON strings
          hobbies: JSON.stringify(request.hobbies || []),
          constraints: JSON.stringify(request.constraints || {}),
        });

        // Note: We expose a GET-like SSE endpoint for simplicity; backend expects POST body
        // If backend strictly requires POST body, we would need fetch + ReadableStream; here we adapt
  const es = new EventSource(apiUrl(`/plan-trip/stream?${params.toString()}`));

        await new Promise<void>((resolve, reject) => {
          es.onmessage = (event) => {
            try {
              const payload = JSON.parse(event.data);
              const stage = payload.stage || 'progress';
              if (stage === 'result' && payload.result) {
                dispatch({ type: 'SEARCH_SUCCESS', payload: payload.result as TripResponse });
                es.close();
                resolve();
              } else if (stage === 'complete') {
                // no-op, wait for result event
              } else {
                dispatch({ type: 'SEARCH_PROGRESS', payload });
              }
            } catch (err) {
              // ignore malformed events but keep stream
            }
          };
          es.onerror = (err) => {
            es.close();
            reject(new Error('Streaming connection error'));
          };
        });
      } else {
        const response = await fetch(apiUrl('/plan-trip'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(request),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to generate trip plan');
        }

        const data: TripResponse = await response.json();
        dispatch({ type: 'SEARCH_SUCCESS', payload: data });
      }
    } catch (error) {
      dispatch({ 
        type: 'SEARCH_ERROR', 
        payload: error instanceof Error ? error.message : 'An unexpected error occurred' 
      });
    }
  };

  const clearResults = () => {
    dispatch({ type: 'CLEAR_RESULTS' });
  };

  return (
    <TripContext.Provider value={{ state, searchTrip, clearResults }}>
      {children}
    </TripContext.Provider>
  );
};

export const useTrip = (): TripContextType => {
  const context = useContext(TripContext);
  if (context === undefined) {
    throw new Error('useTrip must be used within a TripProvider');
  }
  return context;
};
