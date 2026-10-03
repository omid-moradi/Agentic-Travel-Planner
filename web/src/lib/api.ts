/**
 * Typed client for the FastAPI backend (/api/v1).
 * The base URL comes from NEXT_PUBLIC_API_BASE (default: localhost:8000).
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface ApiError {
  code: string;
  message: string;
  request_id: string;
  details?: unknown;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  const text = await response.text();
  const body = text ? JSON.parse(text) : {};
  if (!response.ok) {
    const err = (body as { error?: ApiError }).error;
    throw new ApiClientError(err?.code ?? "unknown", err?.message ?? response.statusText, response.status);
  }
  return body as T;
}

export class ApiClientError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

// ---------------------------------------------------------------- trip types
export interface TripSummary {
  id: string;
  title: string;
  status: "planning" | "done" | "failed";
  region: string;
  language: string;
  start_date: string | null;
  duration_nights: number;
  travelers: number;
  created_at: string;
}

export interface Activity {
  place: {
    name: string;
    address?: string;
    description?: string;
    status: string;
    source?: { name: string; url?: string | null } | null;
  };
  start_time: string;
  end_time: string;
  transport_to_next?: {
    mode: string;
    distance_km: number;
    duration_minutes: number;
  } | null;
}

export interface DayPlan {
  day_number: number;
  date: string;
  city: string;
  accommodation?: { name: string } | null;
  activities: Activity[];
  daily_budget?: { amount: number; status: string; note?: string } | null;
  notes: string[];
}

export interface ItineraryPayload {
  days: DayPlan[];
  total_cost?: { amount: number; status: string; note?: string } | null;
}

export interface ItineraryResponse {
  trip_id: string;
  version: number;
  is_valid: boolean;
  total_cost: number | null;
  currency: string | null;
  payload: ItineraryPayload;
}

export interface TraceItem {
  node: string;
  status: string;
  tokens: number;
  duration_ms: number;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface SharedTrip {
  trip: {
    title: string;
    region: string;
    language: string;
    start_date: string | null;
    duration_nights: number;
  };
  itinerary: {
    version: number;
    is_valid: boolean;
    total_cost: number | null;
    currency: string | null;
    payload: ItineraryPayload;
  } | null;
  read_only: boolean;
}

// ------------------------------------------------------------------- api fns
export const api = {
  createTrip: (body: {
    request: string;
    region?: string;
    language?: string;
    duration_nights?: number;
    travelers?: number;
  }) =>
    request<TripSummary>("/api/v1/trips", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listTrips: () => request<{ items: TripSummary[]; count: number }>("/api/v1/trips"),

  getTrip: (id: string) => request<TripSummary>(`/api/v1/trips/${id}`),

  getItinerary: (id: string) =>
    request<ItineraryResponse>(`/api/v1/trips/${id}/itinerary`),

  getTrace: (id: string) =>
    request<{ items: TraceItem[] }>(`/api/v1/trips/${id}/trace`),

  replan: (id: string) =>
    request<TripSummary>(`/api/v1/trips/${id}/replan`, { method: "POST" }),

  createShare: (id: string) =>
    request<{ trip_id: string; token: string; share_url: string }>(
      `/api/v1/trips/${id}/share`,
      { method: "POST" },
    ),

  getShared: (token: string) => request<SharedTrip>(`/api/v1/share/${token}`),
};
