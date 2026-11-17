import type { TicketStatus as Status } from "@/api/assignments";
import { TICKET_DOT, TICKET_LABEL } from "@/lib/tickets";

// ticket status as a coloured dot plus words, matching StatusLabel; an overdue ticket also says so
export function TicketStatus({ status, overdue = false }: { status: Status; overdue?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-sm font-medium">
      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: TICKET_DOT[status] }} aria-hidden="true" />
      {TICKET_LABEL[status]}
      {overdue ? <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-semibold text-rose-800">Overdue</span> : null}
    </span>
  );
}
