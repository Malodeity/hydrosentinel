// The page frame: top navigation, the headline on the dashboard, and the route table.
//   /          public dashboard (pages/DashboardPage.tsx)
//   /reports   resident report form + status lookup (pages/ReportPage.tsx)
//   /login     admin sign-in (pages/LoginPage.tsx)
//   /admin     admin console, login required (pages/AdminPage.tsx); /admin/report is the printable management report
//   /tickets   a contractor's own repair tickets (pages/ContractorTicketsPage.tsx)

import { Link, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { ShieldCheck, Waves, MapPinned, Wrench } from "lucide-react";

import { authStorage } from "@/api/client";
import { ChangePassword } from "@/components/ChangePassword";
import { NotificationBell } from "@/components/NotificationBell";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Button } from "@/components/ui/button";
import { DashboardPage } from "@/pages/DashboardPage";
import { LoginPage } from "@/pages/LoginPage";
import { ReportPage } from "@/pages/ReportPage";
import { AdminPage } from "@/pages/AdminPage";
import { ManagementReportPage } from "@/pages/ManagementReportPage";
import { ContractorTicketsPage } from "@/pages/ContractorTicketsPage";

// the page frame: header, navigation and the route table. print:hidden hides the header when an admin prints the management report
function AppShell() {
  // this reads the current route and saved user so the nav and sign-out button stay in sync
  const location = useLocation();
  const navigate = useNavigate();
  const user = authStorage.getUser();
  const showHero = location.pathname === "/";

  return (
    <div className="min-h-screen">
      <header className="relative z-[1200] border-b border-border/70 bg-background/90 backdrop-blur-md print:hidden">
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
            {user?.role === "contractor" ? (
              <Button asChild variant={location.pathname.startsWith("/tickets") ? "default" : "outline"}>
                <Link to="/tickets">
                  <Wrench className="h-4 w-4" />
                  My tickets
                </Link>
              </Button>
            ) : (
              <Button asChild variant={location.pathname.startsWith("/admin") ? "default" : "outline"}>
                <Link to="/admin">
                  <ShieldCheck className="h-4 w-4" />
                  Admin
                </Link>
              </Button>
            )}
            {user ? <NotificationBell /> : null}
            {user ? <ChangePassword /> : null}
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

      <main className="mx-auto max-w-7xl px-4 py-8 print:max-w-none print:p-0">
        {showHero ? (
          <section className="mb-8">
            <h2 className="text-4xl font-semibold tracking-tight">South Africa's water services, at a glance.</h2>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
              Built from the Department of Water and Sanitation's 2023 audits (Blue Drop, Green Drop, No Drop) and National Treasury data, plus reports from residents.
              Risk levels are AI-assisted estimates, not official ratings.
            </p>
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
          {/* admin only: the management report, which prints to a four-page A4 pdf */}
          <Route
            path="/admin/report"
            element={
              <ProtectedRoute requireRole="admin">
                <ManagementReportPage />
              </ProtectedRoute>
            }
          />
          {/* contractor accounts only: their own repair tickets */}
          <Route
            path="/tickets"
            element={
              <ProtectedRoute requireRole="contractor">
                <ContractorTicketsPage />
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
