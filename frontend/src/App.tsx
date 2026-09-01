import { Link, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { ShieldCheck, Waves, MapPinned } from "lucide-react";

import { authStorage } from "@/api/client";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Button } from "@/components/ui/button";
import { DashboardPage } from "@/pages/DashboardPage";
import { LoginPage } from "@/pages/LoginPage";
import { ReportPage } from "@/pages/ReportPage";
import { AdminPage } from "@/pages/AdminPage";

function AppShell() {
  // this reads the current route and saved user so the nav and sign-out button stay in sync
  const location = useLocation();
  const navigate = useNavigate();
  const user = authStorage.getUser();
  const showHero = location.pathname === "/";

  return (
    <div className="min-h-screen">
      <header className="border-b border-border/70 bg-background/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-5 lg:flex-row lg:items-center lg:justify-between">
          <Link to="/" className="text-xl font-semibold tracking-tight">
            HydroSentinel
          </Link>
          <nav className="flex flex-wrap items-center gap-2">
            <Button asChild variant={location.pathname === "/" ? "default" : "outline"}>
              <Link to="/">
                <MapPinned className="h-4 w-4" />
                Dashboard
              </Link>
            </Button>
            <Button asChild variant={location.pathname === "/reports" ? "default" : "outline"}>
              <Link to="/reports">
                <Waves className="h-4 w-4" />
                Report Issue
              </Link>
            </Button>
            <Button asChild variant={location.pathname === "/admin" ? "default" : "outline"}>
              <Link to="/admin">
                <ShieldCheck className="h-4 w-4" />
                Admin
              </Link>
            </Button>
            {user ? (
              <Button
                variant="ghost"
                onClick={() => {
                  // this clears the saved login and sends the user back to the login page
                  authStorage.clearSession();
                  navigate("/login");
                }}
              >
                Sign out
              </Button>
            ) : (
              <Button asChild variant={location.pathname === "/login" ? "secondary" : "ghost"}>
                <Link to="/login">Sign in</Link>
              </Button>
            )}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8">
        {showHero ? (
          <section className="mb-8">
            <h2 className="text-4xl font-semibold tracking-tight">South Africa's water services, tracked in real time.</h2>
          </section>
        ) : null}

        <Routes>
          {/* this switches between the public dashboard pages and the protected admin page */}
          <Route path="/" element={<DashboardPage />} />
          <Route path="/reports" element={<ReportPage />} />
          <Route
            path="/admin"
            element={
              <ProtectedRoute requireRole="admin">
                <AdminPage />
              </ProtectedRoute>
            }
          />
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return <AppShell />;
}
