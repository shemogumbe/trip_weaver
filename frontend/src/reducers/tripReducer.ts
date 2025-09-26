import { AppState, TripRequest, TripResponse } from '../types';

export type TripAction =
  | { type: 'SEARCH_START'; payload: TripRequest }
  | { type: 'SEARCH_SUCCESS'; payload: TripResponse }
  | { type: 'SEARCH_ERROR'; payload: string }
  | { type: 'SEARCH_PROGRESS'; payload: any }
  | { type: 'CLEAR_RESULTS' };

export const tripReducer = (state: AppState, action: TripAction): AppState => {
  switch (action.type) {
    case 'SEARCH_START':
      return {
        ...state,
        isLoading: true,
        error: null,
        lastSearch: action.payload,
      };

    case 'SEARCH_SUCCESS':
      return {
        ...state,
        isLoading: false,
        tripPlan: action.payload.plan,
        logs: action.payload.logs,
        error: null,
      };

    case 'SEARCH_PROGRESS':
      return {
        ...state,
        // keep loading while we receive progress events
        isLoading: true,
        // append new log/event to the list
        logs: [...state.logs, action.payload],
      };

    case 'SEARCH_ERROR':
      return {
        ...state,
        isLoading: false,
        error: action.payload,
        tripPlan: null,
        logs: [],
      };

    case 'CLEAR_RESULTS':
      return {
        ...state,
        tripPlan: null,
        logs: [],
        error: null,
        lastSearch: null,
      };

    default:
      return state;
  }
};
