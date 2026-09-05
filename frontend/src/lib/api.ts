/** Typed client for the BridgeFlow backend. Mirrors backend/src/bridgeflow/schemas. */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Department = "production" | "procurement" | "finance" | "marketing";
export type Severity = "info" | "watch" | "warning" | "critical";

export interface Evidence {
  period: string;
  entity_id: string;
  metric: string;
  value: number;
  comparison: string | null;
}

export interface Finding {
  role: Department;
  severity: Severity;
  claim: string;
  evidence: Evidence[];
  suggested_action: string;
}

export interface MasterTable {
  grain: "month" | "quarter" | "year";
  periods: string[];
  rows: Record<string, unknown>[];
}

export interface RiskReport {
  period: string;
  findings: Finding[];
  tensions: { finding_a: Finding; finding_b: Finding; description: string }[];
  cards: unknown[];
}

export interface PipelineResult {
  period: string;
  clean_tables: unknown[];
  graph: { entities: unknown[]; links: unknown[]; unresolved: unknown[] };
  master_table: MasterTable;
  risk_report: RiskReport | null;
}

/** Upload one month of departmental exports and run the full pipeline. */
export async function analyze(
  period: string,
  files: { department: Department; file: File }[],
): Promise<PipelineResult> {
  const body = new FormData();
  body.append("period", period);
  for (const { department, file } of files) {
    body.append("departments", department);
    body.append("files", file);
  }

  const response = await fetch(`${BASE_URL}/analyze`, { method: "POST", body });
  if (!response.ok) {
    throw new Error(`analyze failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}
