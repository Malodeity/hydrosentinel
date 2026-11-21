// What an admin tab looks like while its data is still coming: the same cards, tiles and table rows, as grey shimmering shapes, so the page
// has its shape from the first moment instead of going blank and then jumping into place. One shape per tab, matching what will replace it.

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

type Tab = "overview" | "reports" | "contractors" | "cap" | "ai" | "users" | "audit";

const Tiles = ({ count }: { count: number }) => (
  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
    {Array.from({ length: count }, (_, n) => (
      <Card key={n}>
        <CardContent className="space-y-3 p-5">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-8 w-16" />
          <Skeleton className="h-3 w-32" />
        </CardContent>
      </Card>
    ))}
  </div>
);

const Rows = ({ title, rows, filters }: { title?: boolean; rows: number; filters?: boolean }) => (
  <Card>
    <CardHeader className="space-y-3">
      {title ? <Skeleton className="h-5 w-48" /> : null}
      <Skeleton className="h-3 w-80 max-w-full" />
      {filters ? (
        <div className="grid gap-3 pt-2 sm:grid-cols-3">
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
        </div>
      ) : null}
    </CardHeader>
    <CardContent className="space-y-3">
      {Array.from({ length: rows }, (_, n) => (
        <div key={n} className="flex items-center gap-4">
          <Skeleton className="h-9 w-9 shrink-0 rounded-full" />
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="hidden h-4 w-28 sm:block" />
          <Skeleton className="h-6 w-16 rounded-full" />
        </div>
      ))}
    </CardContent>
  </Card>
);

const Blocks = ({ count }: { count: number }) => (
  <div className="grid gap-4 lg:grid-cols-2">
    {Array.from({ length: count }, (_, n) => (
      <Card key={n}>
        <CardContent className="space-y-3 p-6">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-11/12" />
          <Skeleton className="h-24 w-full" />
        </CardContent>
      </Card>
    ))}
  </div>
);

export function TabSkeleton({ tab }: { tab: Tab }) {
  return (
    <div className="space-y-6" aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading</span>
      {tab === "overview" ? (
        <>
          <Tiles count={4} />
          <Rows title rows={4} />
          <Rows rows={5} />
        </>
      ) : null}
      {tab === "reports" ? (
        <>
          <Rows title rows={0} filters />
          <Blocks count={2} />
          <Rows rows={7} />
        </>
      ) : null}
      {tab === "contractors" ? (
        <>
          <Tiles count={4} />
          <Rows title rows={3} filters />
          <Blocks count={2} />
        </>
      ) : null}
      {tab === "cap" ? (
        <>
          <Rows title rows={0} filters />
          <Blocks count={2} />
          <Rows rows={8} />
        </>
      ) : null}
      {tab === "ai" ? <Blocks count={2} /> : null}
      {tab === "users" ? (
        <>
          <Rows title rows={0} filters />
          <Rows rows={6} />
        </>
      ) : null}
      {tab === "audit" ? <Rows title rows={10} filters /> : null}
    </div>
  );
}
