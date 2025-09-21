export interface Dimension {
  id: number;
  name: string;
  description?: string | null;
  image_filename?: string | null;
  image_alt?: string | null;
  theme_count?: number | null;
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

export interface TopicDetail {
  id: number;
  name: string;
  description?: string | null;
  rating_level?: number | null;
  is_na: boolean;
  comment?: string | null;
  guidance: Record<number, string[]>;
}

export interface ThemeTopicsResponse {
  theme: Theme;
  topics: TopicDetail[];
  rating_scale: RatingScaleItem[];
  generic_guidance: ThemeLevelGuidanceItem[];
}

export interface SessionListItem {
  id: number;
  name: string;
  assessor?: string | null;
  organization?: string | null;
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
  rating_level?: number | null;
  is_na: boolean;
  comment?: string | null;
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
