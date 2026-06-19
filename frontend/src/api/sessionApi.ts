import axiosClient from './axiosClient';
import type {
  GetSessionsResponse,
  DeleteSessionResponse,
  GetSessionsParams,
} from '@/types/api.types';
import type { Session } from '@/types/session.types';
import type { ApiResponse } from '@/types/api.types';

// ===== GET /sessions — Danh sách phiên =====
export const getSessions = async (
  params?: GetSessionsParams
): Promise<GetSessionsResponse> => {
  const response = await axiosClient.get<GetSessionsResponse>('/sessions', { params });
  return response.data;
};

// ===== GET /sessions/:id — Chi tiết phiên =====
export const getSessionById = async (
  sessionId: string
): Promise<ApiResponse<Session>> => {
  const response = await axiosClient.get<ApiResponse<Session>>(`/sessions/${sessionId}`);
  return response.data;
};

// ===== DELETE /sessions/:id — Xóa phiên =====
export const deleteSession = async (
  sessionId: string
): Promise<DeleteSessionResponse> => {
  const response = await axiosClient.delete<DeleteSessionResponse>(`/sessions/${sessionId}`);
  return response.data;
};

export const deleteAllSessions = async (): Promise<DeleteSessionResponse> => {
  const response = await axiosClient.delete<DeleteSessionResponse>('/sessions');
  return response.data;
};
