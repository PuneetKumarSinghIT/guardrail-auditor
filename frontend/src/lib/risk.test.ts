import { describe, expect, it } from "vitest";
import { hasFix, riskBand, sortBySeverity, statusStyle } from "./risk";
import type { Finding } from "./types";

function finding(partial: Partial<Finding>): Finding {
  return {
    finding_id: partial.finding_id ?? "f",
    scan_job_id: "s",
    rule_id: partial.rule_id ?? "R-000",
    severity: partial.severity ?? "LOW",
    resource_name: "res",
    ai_fix_code: partial.ai_fix_code,
  };
}

describe("riskBand", () => {
  it("maps scores to the four CLAUDE.md thresholds", () => {
    expect(riskBand(0).label).toBe("Low Risk");
    expect(riskBand(30).label).toBe("Low Risk");
    expect(riskBand(31).label).toBe("Medium Risk");
    expect(riskBand(60).label).toBe("Medium Risk");
    expect(riskBand(61).label).toBe("High Risk");
    expect(riskBand(80).label).toBe("High Risk");
    expect(riskBand(81).label).toBe("Critical Risk");
    expect(riskBand(100).label).toBe("Critical Risk");
  });

  it("uses red for a high score (> 60)", () => {
    expect(riskBand(70).color).toBe("#dc2626");
  });
});

describe("sortBySeverity", () => {
  it("orders CRITICAL → HIGH → MEDIUM → LOW", () => {
    const input = [
      finding({ finding_id: "a", severity: "LOW" }),
      finding({ finding_id: "b", severity: "CRITICAL" }),
      finding({ finding_id: "c", severity: "MEDIUM" }),
      finding({ finding_id: "d", severity: "HIGH" }),
    ];
    const order = sortBySeverity(input).map((f) => f.severity);
    expect(order).toEqual(["CRITICAL", "HIGH", "MEDIUM", "LOW"]);
  });

  it("does not mutate the input array", () => {
    const input = [
      finding({ severity: "LOW" }),
      finding({ severity: "CRITICAL" }),
    ];
    sortBySeverity(input);
    expect(input[0].severity).toBe("LOW");
  });
});

describe("hasFix", () => {
  it("is true only for CRITICAL/HIGH with fix code (cost guard)", () => {
    expect(hasFix(finding({ severity: "CRITICAL", ai_fix_code: "x" }))).toBe(true);
    expect(hasFix(finding({ severity: "HIGH", ai_fix_code: "x" }))).toBe(true);
    expect(hasFix(finding({ severity: "MEDIUM", ai_fix_code: "x" }))).toBe(false);
    expect(hasFix(finding({ severity: "CRITICAL" }))).toBe(false);
  });
});

describe("statusStyle", () => {
  it("labels known statuses and falls back gracefully", () => {
    expect(statusStyle("COMPLETE").label).toBe("Complete");
    expect(statusStyle("QUEUED").label).toBe("Queued");
    expect(statusStyle("FAILED").className).toContain("red");
  });
});
