import { apiClient } from "@/api/client";

export type UserRole = "admin" | "viewer";

export interface AdminUser {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export async function fetchUsers() {
  const { data } = await apiClient.get<AdminUser[]>("/users");
  return data;
}

export async function createUser(payload: { email: string; password: string; role: UserRole }) {
  const { data } = await apiClient.post<AdminUser>("/users", payload);
  return data;
}

export async function setUserActive(userId: string, isActive: boolean) {
  const { data } = await apiClient.patch<AdminUser>(`/users/${userId}`, { is_active: isActive });
  return data;
}
