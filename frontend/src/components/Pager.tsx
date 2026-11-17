// 'Showing 1-8 of 120' with Previous / Next. The page maths is in lib/pagination.ts.

import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { Page } from "@/lib/pagination";

interface PagerProps {
  page: Page<unknown>;
  noun: string; // e.g. "reports"
  onPageChange: (page: number) => void;
}

export function Pager({ page, noun, onPageChange }: PagerProps) {
  if (page.total === 0) return null;
  const label = page.total === 1 ? noun.replace(/ies$/, "y").replace(/s$/, "") : noun; // 1 report, 2 reports
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 pt-2 text-sm text-muted-foreground">
      <span>
        Showing {page.start}&ndash;{page.end} of {page.total} {label}
      </span>
      {page.pageCount > 1 ? (
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" disabled={page.page <= 1} onClick={() => onPageChange(page.page - 1)} aria-label="Previous page">
            <ChevronLeft className="h-4 w-4" />
            Prev
          </Button>
          <span className="min-w-[5rem] text-center">
            Page {page.page} of {page.pageCount}
          </span>
          <Button size="sm" variant="outline" disabled={page.page >= page.pageCount} onClick={() => onPageChange(page.page + 1)} aria-label="Next page">
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      ) : null}
    </div>
  );
}
