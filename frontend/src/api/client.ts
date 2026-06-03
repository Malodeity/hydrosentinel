import axios from "axios";

export type UserRole = "admin" | "viewer";

export interface StoredUser {
  id: string;
  email: string;
  role: UserRole;
  created_at: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: StoredUser;
}

const TOKEN_KEY = "hydrosentinel_token";
const USER_KEY = "hydrosentinel_user";

// this creates one axios client so every api file talks to the same backend base url
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  // this automatically adds the saved jwt to every request after login
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authStorage = {
  setSession(response: LoginResponse) {
    // this saves the jwt and user details in local storage so page refreshes keep the login
    localStorage.setItem(TOKEN_KEY, response.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(response.user));
  },
  clearSession() {
    // this removes the saved login when the user signs out
    localStorage.removeItem(TOKEN_KEY);
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
    // this calls the backend login route and returns the token response
    const { data } = await apiClient.post<LoginResponse>("/auth/login", payload);
    return data;
  },
  async me() {
    const { data } = await apiClient.get<StoredUser>("/auth/me");
    return data;
  },
};
