// Central configuration for the SupplyTwin API Base URL
// Can be overridden in production by setting VITE_API_BASE_URL in the .env file
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';
