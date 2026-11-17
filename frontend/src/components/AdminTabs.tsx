// The tab bar at the top of the admin console. Arrow keys move between tabs; `count` is the red badge and `countLabel` is what it means on hover.

import { type KeyboardEvent, type ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface AdminTab<Id extends string> {
  id: Id;
  label: string;
  count?: number; // a badge for things that need attention
  countLabel?: string; // what the badge counts, shown on hover (a bare number does not say)
}

interface AdminTabsProps<Id extends string> {
  tabs: AdminTab<Id>[];
  active: Id;
  onChange: (id: Id) => void;
  trailing?: ReactNode; // an action shown at the right of the bar, whichever tab is open
}

export function AdminTabs<Id extends string>({ tabs, active, onChange, trailing }: AdminTabsProps<Id>) {
  // arrow keys move between tabs, as people expect from a tab bar
  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    event.preventDefault();
    const next = tabs[(index + step + tabs.length) % tabs.length];
    onChange(next.id);
    document.getElementById(`admin-tab-${next.id}`)?.focus();
  };

  return (
    <div className="sticky top-0 z-[1100] -mx-4 border-b border-border/70 bg-background/90 px-4 py-3 backdrop-blur-md">
      <div className="flex items-center gap-3">
      <div role="tablist" aria-label="Admin sections" className="flex min-w-0 flex-1 gap-2 overflow-x-auto pb-1">
        {tabs.map((tab, index) => {
          const selected = tab.id === active;
          return (
            <button
              key={tab.id}
              id={`admin-tab-${tab.id}`}
              type="button"
              role="tab"
              aria-selected={selected}
              aria-controls={`admin-panel-${tab.id}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(tab.id)}
              onKeyDown={(event) => onKeyDown(event, index)}
              className={cn(
                "inline-flex shrink-0 items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                selected ? "border-primary bg-primary text-primary-foreground shadow-sm" : "border-border bg-background/80 text-foreground hover:bg-secondary",
              )}
            >
              {tab.label}
              {tab.count ? (
                <span
                  title={tab.countLabel}
                  className={cn(
                    "rounded-full px-2 py-0.5 text-xs font-semibold",
                    selected ? "bg-white/25 text-primary-foreground" : "bg-rose-100 text-rose-800",
                  )}
                >
                  {tab.count}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
      {trailing ? <div className="shrink-0 pb-1">{trailing}</div> : null}
      </div>
    </div>
  );
}
