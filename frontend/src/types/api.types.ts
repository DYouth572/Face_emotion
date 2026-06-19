import type { SessionReport }  from "./report.types";
import type { SessionSummary } from "./session.types";

export interface ApiResponse<T> {
  success:   boolean;
  data:      T;
  message?:  string;
  errorCode?: string;
}

export interface ApiErrorResponse {
  success:   false;
  message:   string;
  errorCode: string;
 
  /** HTTP status code */
  status:    number;
}

export interface PaginationMeta {
  page:       number;
  pageSize:   number;
  total:      number;
  totalPages: number;
}
 
export interface PaginatedResponse<T> {
  items:      T[];
  pagination: PaginationMeta;
}

/** GET /sessions — danh sách phiên đã lưu */
export type GetSessionsResponse = ApiResponse<PaginatedResponse<SessionSummary>>;
 
/** GET /sessions/:id/report — báo cáo chi tiết */
export type GetReportResponse = ApiResponse<SessionReport>;
 
/** DELETE /sessions/:id */
export type DeleteSessionResponse = ApiResponse<{ deleted: boolean }>;


export interface HealthCheckResponse {
  status:    "ok" | "degraded" | "error";
  version:   string;
 
  /** Các service phụ thuộc */
  services: {
    camera:    boolean;
    mediapipe: boolean;
    deepface:  boolean;
    database:  boolean;
  };
 
  /** Unix ms */
  checkedAt: number;
}
 
export type GetHealthResponse = ApiResponse<HealthCheckResponse>;

export interface GetSessionsParams {
  page?:     number;
  pageSize?: number;
 
  /** Lọc theo khoảng thời gian */
  fromDate?: number;   // Unix ms
  toDate?:   number;
 
  /** Sắp xếp */
  sortBy?:   "startedAt" | "durationMs" | "avgStressScore";
  order?:    "asc" | "desc";
}