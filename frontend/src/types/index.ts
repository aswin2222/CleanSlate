export interface User {
  id: string;
  email: string;
  role: string;
  created_at: string;
}

export interface Dataset {
  id: string;
  owner_id: string;
  filename: string;
  sha256_original: string;
  canonical_hash: string;
  format: string;
  rows: number;
  cols: number;
  size_bytes: number;
  created_at: string;
  quarantined_count: number;
  cloudinary_url?: string;
}

export interface UploadGuardResponse {
  is_valid: boolean;
  error_code?: string;
  message: string;
  dataset?: Dataset;
  quarantined_count: number;
  null_bytes_stripped: number;
  formula_injection_cells_detected: number;
}

export interface Run {
  id: string;
  dataset_id: string;
  status: string;
  llm_mode: string;
  config_json: string;
  created_at: string;
  updated_at: string;
}

export interface ColumnProfile {
  column_name: string;
  total_count: number;
  missing_count: number;
  null_rate: number;
  distinct_count: number;
  top_values: [string, number][];
  inferred_types: Record<string, number>;
  primary_type: string;
  is_mixed_type: boolean;
  pattern_signatures: [string, number][];
  format_variants: Record<string, number>;
  leading_trailing_whitespace_count: number;
  case_inconsistencies: number;
  is_numeric: boolean;
  numeric_count: number;
  min_value?: number;
  max_value?: number;
  mean?: number;
  median?: number;
  std?: number;
  iqr_outliers_count: number;
  mad_outliers_count: number;
  is_extreme_sparse: boolean;
}

export interface DatasetProfile {
  fingerprint: string;
  total_rows: number;
  total_columns: number;
  columns: Record<string, ColumnProfile>;
  exact_duplicate_rows: number;
  near_duplicate_candidates_count: number;
  sparsity_report: {
    dataset_sparsity_rate: number;
    is_low_evidence: boolean;
    extreme_sparse_columns: string[];
    summary_sentence: string;
  };
  summary_text: string;
}

export interface Rule {
  id: string;
  kind: string;
  columns: string[];
  params: Record<string, any>;
  support: number;
  confidence: number;
  source: string;
  status: string;
  evidence: string;
  violation_count?: number;
  violating_rids?: number[];
}

export interface DryRunResult {
  rows_removed: number;
  rows_removed_pct: number;
  cells_modified: number;
  cells_modified_pct: number;
  non_null_cells_destroyed: number;
  loss_score: number;
  loss_label: 'LOW' | 'MEDIUM' | 'HIGH';
  human_summary: string;
}

export interface PlanStep {
  id: string;
  seq: number;
  transformation: string;
  params: Record<string, any>;
  rationale: string;
  requires_approval: boolean;
  approved: boolean;
  loss_score: number;
  loss_label: string;
  predicted_loss: DryRunResult;
  status: string;
}

export interface RollbackResponse {
  success: boolean;
  hash_original: string;
  hash_current: string;
  matches_original: boolean;
  reverted_steps_count: number;
  message: string;
}

export interface TestResultItem {
  name: string;
  rule_id?: string;
  outcome: string;
  message: string;
}

export interface SuiteRunReport {
  stage: string;
  passed: number;
  failed: number;
  total: number;
  results: TestResultItem[];
  fixed_violations: string[];
  remaining_violations: string[];
  regressions: string[];
}

export interface MutationReport {
  total_mutations: number;
  detected_mutations: number;
  fault_detection_rate_pct: number;
  mutations: {
    mutation_type: string;
    target_column: string;
    row_index: number;
    detected: boolean;
    diagnostic: string;
  }[];
}
