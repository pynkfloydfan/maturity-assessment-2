export interface Dimension {
  id: number;
  name: string;
  description?: string | null;
  image_filename?: string | null;
  image_alt?: string | null;
  theme_count?: number | null;
  topic_count?: number | null;
}

export interface Theme {
  id: number;
  dimension_id: number;
  name: string;
  description?: string | null;
  category?: string | null;
  topic_count?: number | null;
}

export interface RatingScaleItem {
  level: number;
  label: string;
  description?: string | null;
}

export interface ThemeLevelGuidanceItem {
  level: number;
  description: string;
}

export type ProgressState = "not_started" | "in_progress" | "complete";

export interface Acronym {
  id: number;
  acronym: string;
  full_term: string;
  meaning?: string | null;
}

export interface TopicDetail {
  id: number;
  name: string;
  description?: string | null;
  impact?: string | null;
  benefits?: string | null;
  basic?: string | null;
  advanced?: string | null;
  evidence?: string | null;
  regulations?: string | null;
  current_maturity?: number | null;
  current_is_na: boolean;
  desired_maturity?: number | null;
  desired_is_na: boolean;
  comment?: string | null;
  evidence_links: string[];
  progress_state: ProgressState;
  guidance: Record<number, string[]>;
}

export interface ThemeTopicsResponse {
  theme: Theme;
  topics: TopicDetail[];
  rating_scale: RatingScaleItem[];
  generic_guidance: ThemeLevelGuidanceItem[];
}

export interface TopicAssessmentDetail extends TopicDetail {
  theme_id: number;
  theme_name: string;
}

export interface ThemeAssessmentBlock {
  id: number;
  name: string;
  description?: string | null;
  category?: string | null;
  topic_count: number;
  topics: TopicAssessmentDetail[];
  generic_guidance: ThemeLevelGuidanceItem[];
}

export interface ProgressSummary {
  total_topics: number;
  completed_topics: number;
  in_progress_topics: number;
  not_started_topics: number;
  completion_percent: number;
}

export interface DimensionAssessmentResponse {
  dimension: Dimension;
  rating_scale: RatingScaleItem[];
  themes: ThemeAssessmentBlock[];
  progress: ProgressSummary;
}

export interface SessionListItem {
  id: number;
  name: string;
  assessor?: string | null;
  created_at: string;
}

export interface SessionSummary extends SessionListItem {
  notes?: string | null;
}

export interface SessionStatistics {
  total_topics: number;
  total_entries: number;
  rated_entries: number;
  na_entries: number;
  computed_entries: number;
  completion_percent: number;
  rating_percent: number;
}

export interface SessionDetail {
  summary: SessionSummary;
  statistics: SessionStatistics;
}

export interface RatingUpdatePayload {
  topic_id: number;
  current_maturity?: number | null;
  desired_maturity?: number | null;
  current_is_na: boolean;
  desired_is_na: boolean;
  comment?: string | null;
  evidence_links?: string[] | null;
  progress_state?: ProgressState;
}

export interface RatingBulkUpdatePayload {
  session_id: number;
  updates: RatingUpdatePayload[];
}

export interface ApiErrorPayload {
  detail?: string;
  message?: string;
}

export interface AverageScore {
  id: number;
  name: string;
  average?: number | null;
  coverage?: number | null;
}

export interface ThemeAverageScore extends AverageScore {
  dimension_id: number;
  dimension_name: string;
}

export interface TopicScore {
  topic_id: number;
  topic_name: string;
  theme_id: number;
  theme_name: string;
  dimension_id: number;
  dimension_name: string;
  score: number;
  source?: "rating" | "computed";
}

export interface DashboardData {
  dimensions: AverageScore[];
  themes: ThemeAverageScore[];
  topic_scores: TopicScore[];
}

export interface DashboardTile {
  id: number;
  name: string;
  average?: number | null;
  coverage?: number | null;
  color?: string | null;
}

export interface PlotlyFigure {
  data: any[];
  layout: Record<string, any>;
  frames?: any[];
  [key: string]: unknown;
}

export interface DashboardFiguresResponse {
  tiles: DashboardTile[];
  radar?: PlotlyFigure | null;
}

export type DatabaseBackend = "sqlite" | "mysql";

export interface DatabaseSettings {
  backend: DatabaseBackend;
  sqlite_path?: string | null;
  mysql_host?: string | null;
  mysql_port?: number | null;
  mysql_user?: string | null;
  mysql_database?: string | null;
}

export interface DatabaseInitRequest {
  backend?: DatabaseBackend;
  sqlite_path?: string | null;
  mysql_host?: string | null;
  mysql_port?: number | null;
  mysql_user?: string | null;
  mysql_password?: string | null;
  mysql_database?: string | null;
}

export interface SeedRequest extends DatabaseInitRequest {
  excel_path?: string | null;
}

export interface DatabaseOperationResponse {
  status: "ok" | "error";
  message: string;
  details?: string | null;
}

export interface SeedResponse extends DatabaseOperationResponse {
  command?: string | null;
  stdout?: string | null;
  stderr?: string | null;
}

export interface ImportResponse extends DatabaseOperationResponse {
  processed: number;
  errors?: {
    field?: string;
    message: string;
    value?: unknown;
    details?: Record<string, unknown>;
  }[] | null;
}
