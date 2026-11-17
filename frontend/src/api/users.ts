// User management API: list, create, activate/deactivate (backend/app/routes/users.py).

import { apiClient } from "@/api/client";

export type UserRole = "admin" | "viewer" | "contractor";

export interface AdminUser {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  wsa_id?: string | null;
  contractor_id?: string | null;
  last_login_at: string | null;
  created_at: string;
}

export async function fetchUsers() {
  const { data } = await apiClient.get<AdminUser[]>("/users");
  return data;
}

export async function createUser(payload: { email: string; password: string; role: UserRole; wsa_id?: string | null; contractor_id?: string | null }) {
  const { data } = await apiClient.post<AdminUser>("/users", payload);
  return data;
}

export async function setUserActive(userId: string, isActive: boolean) {
  const { data } = await apiClient.patch<AdminUser>(`/users/${userId}`, { is_active: isActive });
  return data;
}

// POST /auth/change-password: the signed-in user changes their own password (other devices are signed out)
export async function changePassword(currentPassword: string, newPassword: string) {
  await apiClient.post("/auth/change-password", { current_password: currentPassword, new_password: newPassword });
}

// PATCH /users/{id}/password: a national admin sets a new password for someone else
export async function resetUserPassword(userId: string, newPassword: string) {
  await apiClient.patch(`/users/${userId}/password`, { new_password: newPassword });
}
