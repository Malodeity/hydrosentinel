import { describe, expect, it } from "vitest";

import type { Contractor } from "@/api/assignments";
import { matchesContractor } from "@/lib/contractorSearch";

const contractor = (over: Partial<Contractor> = {}): Contractor => ({
  id: "1",
  name: "Radebe Plumbing Services",
  contact_name: "Thandi Radebe",
  phone: "011 555 0100",
  email: "thandi@radebe.example",
  is_active: true,
  coverage: [{ wsa_id: "w1", wsa_name: "City of Ekurhuleni", issue_types: ["leak"] }],
  open_tickets: 0,
  ...over,
});

describe("matchesContractor", () => {
  it("shows everyone when nothing is typed, so an empty box never hides a contractor", () => {
    expect(matchesContractor(contractor(), "")).toBe(true);
    expect(matchesContractor(contractor(), "   ")).toBe(true);
  });

  it("finds a contractor by the authority it serves, which is how an admin thinks about who can take a report", () => {
    expect(matchesContractor(contractor(), "ekurhuleni")).toBe(true);
    expect(matchesContractor(contractor(), "johannesburg")).toBe(false);
  });

  it("needs every word to match, so adding a word narrows the list instead of widening it", () => {
    expect(matchesContractor(contractor(), "plumbing ekurhuleni")).toBe(true);
    expect(matchesContractor(contractor(), "plumbing johannesburg")).toBe(false);
  });

  it("ignores case and survives a contractor with no contact details", () => {
    const bare = contractor({ contact_name: null, phone: null, email: null, coverage: [] });
    expect(matchesContractor(bare, "RADEBE")).toBe(true);
    expect(matchesContractor(bare, "thandi")).toBe(false);
  });
});
