/**
 * lib/types.ts
 * TypeScript mirror of contracts/schemas.py — source of truth is the Python file.
 * Do NOT change field names without syncing with contracts/schemas.py.
 */

// ---------------------------------------------------------------------------
// Shared enums
// ---------------------------------------------------------------------------

export type DifficultyLevel = "beginner" | "intermediate" | "advanced";

export type NodeStatus =
  | "pending"
  | "in_progress"
  | "completed"
  | "failed"
  | "skipped";

export type PatchTrigger =
  | "quiz_failure"
  | "module_skip"
  | "quiz_pass"
  | "manual_recalibrate";

export type EdgeType = "prerequisite" | "recommended" | "remediation";

// ---------------------------------------------------------------------------
// Phase 3 → Frontend  (RoadmapGraphResponse)
// ---------------------------------------------------------------------------

export interface ShapValues {
  gap_severity: number;
  tag_similarity: number;
  course_rating: number;
  difficulty_match: number;
  prereq_satisfaction: number;
}

export interface RoadmapNodeData extends Record<string, unknown> {
  course_id: string;
  title: string;
  platform: string;
  difficulty: DifficultyLevel;
  duration_hours: number;
  skill_tags: string[];
  score: number;
  shap_values: ShapValues;
  explanation_text: string;
  url: string;
  status: NodeStatus;
  is_unlocked: boolean;
}

export interface RoadmapNode {
  id: string;
  type: string; // "courseNode"
  position: { x: number; y: number };
  data: RoadmapNodeData;
}

export interface RoadmapEdge {
  id: string;
  source: string;
  target: string;
  type: EdgeType;
  animated: boolean;
  label: string;
}

export interface RoadmapGraphResponse {
  learner_id: string;
  target_role: string;
  nodes: RoadmapNode[];
  edges: RoadmapEdge[];
  topological_order: string[];
  total_hours: number;
  generated_at: string;
}

// ---------------------------------------------------------------------------
// Phase 4 → Frontend  (RoadmapPatchEvent via SSE)
// ---------------------------------------------------------------------------

export interface PatchedNode {
  id: string;
  label: string;
  status: NodeStatus;
  position?: { x: number; y: number };
}

export interface RoadmapPatchEvent {
  event: "graph_patch";
  learner_id: string;
  trigger: PatchTrigger;
  added_nodes: PatchedNode[];
  removed_node_ids: string[];
  updated_nodes: PatchedNode[];
  added_edges: RoadmapEdge[];
  removed_edge_ids: string[];
  summary: string;
  remediation_path: string[];
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Frontend → Phase 4  (RecalibrateRequest)
// ---------------------------------------------------------------------------

export interface RecalibrateRequest {
  learner_id: string;
  trigger: PatchTrigger;
  node_id: string;
  quiz_score?: number;
  retry_count?: number;
}

// ---------------------------------------------------------------------------
// Learner intake
// ---------------------------------------------------------------------------

export interface LearnerIntakeForm {
  name: string;
  target_role: string;
  self_reported_skills: string[];
  experience_years: number;
  weekly_hours: number; // UI-only, not in backend schema
}

// ---------------------------------------------------------------------------
// Quiz
// ---------------------------------------------------------------------------

export interface QuizQuestion {
  question_id: string;
  question_text: string;
  options: string[];
  correct_option: string;
  difficulty: DifficultyLevel;
  skill_tag: string;
}
