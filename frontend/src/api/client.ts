import axios from "axios";

export type UserRole = "admin" | "viewer";

export interface StoredUser {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: StoredUser;
}

const TOKEN_KEY = "hydrosentinel_token";
const REFRESH_TOKEN_KEY = "hydrosentinel_refresh_token";
const USER_KEY = "hydrosentinel_user";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// on 401 try to refresh once, then clear session and redirect to login
let _refreshing = false;
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retried && !_refreshing) {
      const rawRefresh = localStorage.getItem(REFRESH_TOKEN_KEY);
      if (rawRefresh) {
        original._retried = true;
        _refreshing = true;
        try {
          const { data } = await axios.post<LoginResponse>(
            `${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/auth/refresh`,
            { refresh_token: rawRefresh },
          );
          authStorage.setSession(data);
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return apiClient(original);
        } catch {
          authStorage.clearSession();
          window.location.href = "/login";
        } finally {
          _refreshing = false;
        }
      } else {
        authStorage.clearSession();
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

export const authStorage = {
  setSession(response: LoginResponse) {
    localStorage.setItem(TOKEN_KEY, response.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, response.refresh_token);
    localStorage.setItem(USER_KEY, JSON.stringify(response.user));
  },
  async clearSession() {
    const rawRefresh = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (rawRefresh) {
      try {
        await axios.post(
          `${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/auth/logout`,
          { refresh_token: rawRefresh },
        );
      } catch {
        // ignore — token may already be expired
      }
    }
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
  getToken() {
    return localStorage.getItem(TOKEN_KEY);
  },
  getUser(): StoredUser | null {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as StoredUser) : null;
  },
};

export const authApi = {
  async login(payload: LoginPayload) {
    const { data } = await apiClient.post<LoginResponse>("/auth/login", payload);
    return data;
  },
  async me() {
    const { data } = await apiClient.get<StoredUser>("/auth/me");
    return data;
  },
};
