// The bell in the header for every signed-in user: new tickets for contractors, accepted / rejected / fixed notices for admins. Checks every minute.

import { useCallback, useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { authStorage } from "@/api/client";

import { fetchNotifications, markAllNotificationsRead, markNotificationRead, type AppNotification } from "@/api/assignments";
import { Button } from "@/components/ui/button";

export function NotificationBell() {
  const [items, setItems] = useState<AppNotification[]>([]);
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    try {
      setItems(await fetchNotifications());
    } catch {
      // the bell is a convenience: a failed check must not disturb the page
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 60_000);
    return () => window.clearInterval(timer);
  }, [load]);

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => {
      if (box.current && !box.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  const unread = items.filter((item) => !item.read_at).length;

  return (
    <div className="relative" ref={box}>
      <Button variant="outline" size="icon" aria-label={unread ? `${unread} unread notifications` : "Notifications"} onClick={() => setOpen((value) => !value)}>
        <Bell className="h-4 w-4" />
        {unread > 0 ? (
          <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-rose-600 px-1 text-[11px] font-semibold text-white">{unread}</span>
        ) : null}
      </Button>
      {open ? (
        <div className="absolute right-0 z-[1300] mt-2 w-80 rounded-2xl border border-border bg-background p-2 shadow-lg">
          <div className="flex items-center justify-between px-2 py-1">
            <p className="text-sm font-semibold">Notifications</p>
            {unread > 0 ? (
              <button
                type="button"
                className="text-xs underline underline-offset-2 text-muted-foreground hover:text-foreground"
                onClick={async () => {
                  await markAllNotificationsRead();
                  await load();
                }}
              >
                Mark all read
              </button>
            ) : null}
          </div>
          <ul className="max-h-80 space-y-1 overflow-y-auto">
            {items.length === 0 ? <li className="px-2 py-3 text-sm text-muted-foreground">Nothing yet.</li> : null}
            {items.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className={`w-full rounded-xl px-2 py-2 text-left text-sm hover:bg-secondary/60 ${item.read_at ? "text-muted-foreground" : ""}`}
                  onClick={async () => {
                    if (!item.read_at) {
                      await markNotificationRead(item.id);
                      await load();
                    }
                    // a ticket notice opens the page where that ticket lives: the contractor's tickets, or the admin's console
                    if (item.assignment_id) {
                      setOpen(false);
                      navigate(authStorage.getUser()?.role === "contractor" ? "/tickets" : "/admin");
                    }
                  }}
                >
                  <span className="block font-medium">{item.title}</span>
                  {item.body ? <span className="block text-xs">{item.body}</span> : null}
                  <span className="block text-[11px] text-muted-foreground">{new Date(item.created_at).toLocaleString()}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
