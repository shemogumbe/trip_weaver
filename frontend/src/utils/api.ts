// Central API base for CRA (REACT_APP_ prefix)
export const API_BASE =
  process.env.REACT_APP_API_BASE?.replace(/\/$/, '') || 'http://localhost:8000';

export const apiUrl = (path: string) => `${API_BASE}${path.startsWith('/') ? '' : '/'}${path}`;
