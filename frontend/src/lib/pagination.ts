export interface Page<T> {
  items: T[];
  page: number;
  pageCount: number;
  total: number;
  start: number; // 1-based index of the first item shown, 0 when empty
  end: number;
}

// Slices one page out of a list. A page past the end (e.g. after a filter shrinks the list) is clamped, never empty.
export function paginate<T>(items: T[], page: number, pageSize: number): Page<T> {
  const total = items.length;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const current = Math.min(Math.max(1, page), pageCount);
  const from = (current - 1) * pageSize;
  const slice = items.slice(from, from + pageSize);
  return { items: slice, page: current, pageCount, total, start: total === 0 ? 0 : from + 1, end: from + slice.length };
}
