/**
 * TriQuery TypeScript API Contracts
 * Maps 1:1 with backend Pydantic models in src/api/schemas.py and src/core/types.py
 */

// =============================================================================
// Engine Types
// =============================================================================

export type EngineType = 'relational' | 'graph' | 'vector' | 'hybrid';

// =============================================================================
// System Health Schemas
// =============================================================================

export interface GraphHealthInfo {
  node_count: number;
  edge_count: number;
  is_healthy: boolean;
}

export interface VectorHealthInfo {
  provider: string;
  dimension: number | null;
  document_count: number;
  is_semantic: boolean;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  is_healthy: boolean;
  backend: string;
  database_name: string;
  host: string;
  port: number;
  table_counts: Record<string, number>;
  graph: GraphHealthInfo;
  vector: VectorHealthInfo;
}

// =============================================================================
// Query Models
// =============================================================================

export interface RelationalSubquery {
  track?: string | null;
  college_id?: number | null;
  hackathon_id?: number | null;
  min_cash_prize?: number | null;
  order_by?: string;
  limit?: number;
}

export interface GraphSubquery {
  start_node?: string | null;
  target_type?: string | null;
  max_depth?: number;
  relationship_types?: string[];
  limit?: number;
}

export interface VectorSubquery {
  query_text: string;
  top_k?: number;
  min_score?: number;
}

export interface FusionConfig {
  strategy?: 'rrf' | 'weighted_sum';
  k_constant?: number;
  weights?: Record<string, number>;
}

export interface UnifiedQuery {
  query_id: string;
  name?: string;
  description?: string;
  relational?: RelationalSubquery | null;
  graph?: GraphSubquery | null;
  vector?: VectorSubquery | null;
  fusion?: FusionConfig | null;
  max_results?: number;
}

// =============================================================================
// Presets Schemas
// =============================================================================

export interface PresetItem {
  preset_id: string;
  name: string;
  description: string;
  target_paradigms: string[];
  query: UnifiedQuery;
}

export interface PresetsResponse {
  total_presets: number;
  presets: PresetItem[];
}

// =============================================================================
// Unified Execution Result Schemas
// =============================================================================

export interface FusedItem {
  entity_id: string;
  title: string;
  rrf_score: number;
  final_rank: number;
  participating_engines: EngineType[];
  engine_ranks: Record<string, number>;
  engine_scores: Record<string, number | null>;
  metadata: Record<string, any>;
  is_filtered_out?: boolean;
  filter_reason?: string | null;
}

export interface QueryPlanStep {
  step_id: number;
  engine: EngineType;
  description: string;
  target_operation: string;
  parameters: Record<string, any>;
  depends_on_steps: number[];
}

export interface QueryPlan {
  query_id: string;
  natural_query: string;
  required_engines: EngineType[];
  steps: QueryPlanStep[];
  estimated_cost_note?: string;
}

export interface UnifiedExecutionResult {
  query_id: string;
  query_name: string;
  success: boolean;
  plan: QueryPlan;
  fused_results: FusedItem[];
  raw_engine_results?: Record<string, any>;
  stage_latencies_ms: Record<string, number>;
  stage_record_counts: Record<string, number>;
  total_latency_ms: number;
  error?: string | null;
}

// =============================================================================
// Explainability Schemas
// =============================================================================

export interface ExplainPlanStep {
  step: number;
  engine: string;
  action: string;
  filters_or_args: Record<string, any>;
  complexity: string;
  depends_on: number[];
}

export interface ExplainResponse {
  query_id: string;
  query_name: string;
  target_paradigms: string[];
  plan_steps: ExplainPlanStep[];
  engines_selected: string[];
  step_dependencies: Record<string, number[]>;
  fusion_strategy: string;
  rrf_formula: string;
  rrf_evidence: {
    k_constant: number;
    mandatory_filters_applied: boolean;
    weights: Record<string, number>;
  };
  time_complexity: string;
  space_complexity: string;
  viva_justifications: Record<string, string>;
}

// =============================================================================
// Relational Schemas
// =============================================================================

export interface TableColumnSchema {
  name: string;
  type: string;
  nullable: boolean;
  primary_key: boolean;
  default: string | null;
}

export interface ForeignKeySchema {
  column: string;
  referenced_table: string;
  referenced_column: string;
}

export interface TableSchema {
  table_name: string;
  row_count: number;
  columns: TableColumnSchema[];
  foreign_keys: ForeignKeySchema[];
}

export interface TablesResponse {
  database: string;
  table_count: number;
  tables: TableSchema[];
}

export interface ProjectRecord {
  project_id: number;
  project_title: string;
  track: string;
  short_summary: string;
  description: string;
  tech_stack: string;
  team_name: string;
  college_name: string;
  college_city: string;
  hackathon_name: string;
  hackathon_year: number;
  prize_category?: string;
  rank_position?: number;
  cash_prize?: string;
  [key: string]: any;
}

export interface ProjectsResponse {
  success: boolean;
  count: number;
  data: ProjectRecord[];
  execution_time_ms: number;
  notes: string[];
}

// =============================================================================
// Graph Schemas
// =============================================================================

export interface GraphNodeItem {
  id: string;
  label: string;
  node_type: string;
  attributes: Record<string, any>;
}

export interface GraphEdgeItem {
  source: string;
  target: string;
  edge_type: string;
  direction: string;
  attributes: Record<string, any>;
}

export interface GraphTopologyResponse {
  node_count: number;
  edge_count: number;
  node_types: Record<string, number>;
  edge_types: Record<string, number>;
  nodes: GraphNodeItem[];
  edges: GraphEdgeItem[];
}

export interface GraphPathRequest {
  source: string;
  target: string;
  directed?: boolean;
}

export interface GraphPathResponse {
  found: boolean;
  source: string;
  target: string;
  length: number;
  path: string[];
  steps: Array<Record<string, any>>;
  message: string;
}

// =============================================================================
// Vector Schemas
// =============================================================================

export interface VectorSearchRequest {
  query: string;
  top_k?: number;
  min_score?: number;
}

export interface VectorSearchItem {
  rank: number;
  score: number;
  entity_id: string;
  project_id: number | null;
  title: string;
  track: string | null;
  short_summary: string | null;
  tech_stack: string | null;
}

export interface VectorSearchResponse {
  success: boolean;
  count: number;
  query: string;
  execution_time_ms: number;
  provider: string;
  results: VectorSearchItem[];
  notes: string[];
}
