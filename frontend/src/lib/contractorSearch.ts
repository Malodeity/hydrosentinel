// Search on the Contractors tab: does a contractor match what the admin typed? Every word typed must be found somewhere in the contractor's
// name, contact person, phone, email or the authorities it serves, so "plumb gauteng" narrows rather than widens. Case and extra spaces do not matter.

import type { Contractor } from "@/api/assignments";

export function matchesContractor(contractor: Contractor, query: string): boolean {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (words.length === 0) return true;
  const haystack = [contractor.name, contractor.contact_name, contractor.phone, contractor.email, ...contractor.coverage.map((row) => row.wsa_name)]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return words.every((word) => haystack.includes(word));
}
