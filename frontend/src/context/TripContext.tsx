import React, { createContext, useContext, useReducer, ReactNode } from 'react';
import { AppState, TripRequest, TripResponse } from '../types';
import { tripReducer } from '../reducers/tripReducer';
import { TripAction } from '../reducers/tripReducer';

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
      const response = await fetch('/plan-trip', {
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
