// "Password" button in the header: a small box where the signed-in user changes their own password.

import { useEffect, useRef, useState } from "react";
import { KeyRound } from "lucide-react";
import { isAxiosError } from "axios";

import { changePassword } from "@/api/users";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function ChangePassword() {
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => {
      if (box.current && !box.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (next.length < 8) {
      setMessage({ ok: false, text: "The new password needs at least 8 characters." });
      return;
    }
    setBusy(true);
    try {
      await changePassword(current, next);
      setCurrent("");
      setNext("");
      setMessage({ ok: true, text: "Password changed. Other devices were signed out." });
    } catch (error) {
      const detail = isAxiosError(error) ? error.response?.data?.detail : null;
      setMessage({ ok: false, text: typeof detail === "string" ? detail : "Could not change the password." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative" ref={box}>
      <Button variant="ghost" size="icon" aria-label="Change password" title="Change password" onClick={() => setOpen((v) => !v)}>
        <KeyRound className="h-4 w-4" />
      </Button>
      {open ? (
        <form onSubmit={submit} className="absolute right-0 z-[1300] mt-2 w-72 space-y-2 rounded-lg border border-border bg-card p-3 shadow-lg">
          <p className="text-sm font-medium">Change password</p>
          <Input type="password" autoComplete="current-password" placeholder="Current password" value={current} onChange={(e) => setCurrent(e.target.value)} required />
          <Input type="password" autoComplete="new-password" placeholder="New password (8+ characters)" value={next} onChange={(e) => setNext(e.target.value)} required />
          {message ? <p role="status" className={`text-xs ${message.ok ? "text-emerald-600" : "text-destructive"}`}>{message.text}</p> : null}
          <Button type="submit" size="sm" disabled={busy} className="w-full">{busy ? "Saving…" : "Save password"}</Button>
        </form>
      ) : null}
    </div>
  );
}
