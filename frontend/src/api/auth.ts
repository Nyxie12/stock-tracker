import { api } from "./client";

export type AuthUser = {
  id: number;
  email: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

export const authApi = {
  register: (email: string, password: string) =>
    api.post<TokenResponse>("/api/auth/register", { email, password }),
  login: (email: string, password: string) =>
    api.post<TokenResponse>("/api/auth/login", { email, password }),
  me: () => api.get<AuthUser>("/api/auth/me"),
};
