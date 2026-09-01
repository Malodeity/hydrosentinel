import { type FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { authApi, authStorage } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("admin@hydrosentinel.co.za");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/admin";

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      const response = await authApi.login({ email, password });
      authStorage.setSession(response);
      navigate(from, { replace: true });
    } catch {
      setError("Login failed. Check your email and password and try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-5xl items-center justify-center">
      <Card className="w-full overflow-hidden">
        <div className="grid lg:grid-cols-[1.05fr_0.95fr]">
          <div className="border-b border-border/70 bg-secondary/40 p-8 lg:border-b-0 lg:border-r">
            <p className="text-sm font-medium uppercase tracking-[0.25em] text-primary">HydroSentinel access</p>
            <h2 className="mt-4 text-4xl font-semibold leading-tight">Sign in to manage corrective action plans and review public reports.</h2>
            <p className="mt-4 max-w-xl text-base leading-7 text-muted-foreground">
              HydroSentinel helps municipal teams and oversight users follow service risk, track issue reporting, and respond faster where water systems need attention.
            </p>
          </div>
          <div className="p-8">
            <CardHeader className="p-0">
              <CardTitle>Admin login</CardTitle>
              <CardDescription>Use your HydroSentinel account to open the admin workspace.</CardDescription>
            </CardHeader>
            <CardContent className="p-0 pt-6">
              <form className="space-y-4" onSubmit={submit}>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Email</label>
                  <Input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Password</label>
                  <Input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
                </div>
                {error ? <div className="rounded-2xl border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</div> : null}
                <Button className="w-full" type="submit" disabled={isLoading}>
                  {isLoading ? "Signing in..." : "Sign in"}
                </Button>
              </form>
            </CardContent>
          </div>
        </div>
      </Card>
    </div>
  );
}
