import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { authStorage, type UserRole } from "@/api/client";

interface ProtectedRouteProps {
  children: ReactNode;
  requireRole?: UserRole;
}

export function ProtectedRoute({ children, requireRole }: ProtectedRouteProps) {
  // this remembers the page the user wanted so login can send them back there afterwards
  const location = useLocation();
  const token = authStorage.getToken();
  const user = authStorage.getUser();

  // this sends logged-out users to the login page before they can see protected content
  if (!token || !user) {
    return <Navigate replace state={{ from: location }} to="/login" />;
  }

  // this blocks users who are logged in but do not have the required role
  if (requireRole && user.role !== requireRole) {
    return <Navigate replace to="/" />;
  }

  return <>{children}</>;
}
