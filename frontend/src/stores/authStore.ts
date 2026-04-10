import { create } from "zustand";
import { authApi, type AuthUser } from "../api/auth";

const TOKEN_KEY = "st_token";

type AuthStatus = "idle" | "loading" | "authed" | "anon";

type AuthStore = {
  token: string | null;
  user: AuthUser | null;
  status: AuthStatus;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  hydrate: () => Promise<void>;
};

function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function writeToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // ignore
  }
}

export const useAuthStore = create<AuthStore>((set, get) => ({
  token: readToken(),
  user: null,
  status: "idle",

  login: async (email, password) => {
    const res = await authApi.login(email, password);
    writeToken(res.access_token);
    set({ token: res.access_token, user: res.user, status: "authed" });
  },

  register: async (email, password) => {
    const res = await authApi.register(email, password);
    writeToken(res.access_token);
    set({ token: res.access_token, user: res.user, status: "authed" });
  },

  logout: () => {
    writeToken(null);
    set({ token: null, user: null, status: "anon" });
  },

  hydrate: async () => {
    const token = get().token;
    if (!token) {
      set({ status: "anon" });
      return;
    }
    set({ status: "loading" });
    try {
      const user = await authApi.me();
      set({ user, status: "authed" });
    } catch {
      writeToken(null);
      set({ token: null, user: null, status: "anon" });
    }
  },
}));

// Token getter for api/client.ts — read lazily so updates are reflected.
export function getAuthToken(): string | null {
  return useAuthStore.getState().token;
}
