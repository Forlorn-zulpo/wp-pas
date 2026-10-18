import { create } from "zustand";
import { apiRequest, getTokens, setTokens } from "../lib/api";

export type UserRole = "admin" | "operator" | "reviewer" | "readonly";

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
}

interface AuthState {
  user: CurrentUser | null;
  status: "idle" | "loading" | "authenticated" | "unauthenticated";
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loadCurrentUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  status: "idle",
  error: null,

  login: async (email, password) => {
    set({ status: "loading", error: null });
    try {
      const tokens = await apiRequest<{ access_token: string; refresh_token: string }>(
        "/auth/login",
        { method: "POST", body: { email, password }, skipAuth: true }
      );
      setTokens(tokens);
      const user = await apiRequest<CurrentUser>("/auth/me");
      set({ user, status: "authenticated", error: null });
    } catch (err) {
      const message = err instanceof Error ? err.message : "登录失败";
      set({ status: "unauthenticated", error: message });
      throw err;
    }
  },

  logout: () => {
    setTokens(null);
    set({ user: null, status: "unauthenticated", error: null });
  },

  loadCurrentUser: async () => {
    if (!getTokens()) {
      set({ status: "unauthenticated" });
      return;
    }
    set({ status: "loading" });
    try {
      const user = await apiRequest<CurrentUser>("/auth/me");
      set({ user, status: "authenticated", error: null });
    } catch {
      setTokens(null);
      set({ user: null, status: "unauthenticated" });
    }
  },
}));

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: "管理员",
  operator: "操作员",
  reviewer: "审核员",
  readonly: "只读用户",
};
