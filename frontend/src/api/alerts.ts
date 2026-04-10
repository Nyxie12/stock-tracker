import { api } from "./client";

export type Alert = {
  id: number;
  symbol: string;
  condition: "above" | "below";
  threshold: number;
  active: boolean;
  last_triggered_at: string | null;
  created_at: string;
};

export type AlertCreate = {
  symbol: string;
  condition: "above" | "below";
  threshold: number;
};

export const alertsApi = {
  list: () => api.get<Alert[]>("/api/alerts"),
  create: (payload: AlertCreate) => api.post<Alert>("/api/alerts", payload),
  setActive: (id: number, active: boolean) => api.patch<Alert>(`/api/alerts/${id}`, { active }),
  remove: (id: number) => api.del<void>(`/api/alerts/${id}`),
};
