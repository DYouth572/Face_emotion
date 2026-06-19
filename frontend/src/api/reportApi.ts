import axiosClient from './axiosClient';
import type { GetReportResponse } from '@/types/api.types';
import type { ReportExportFormat } from '@/types/report.types';

export const getSessionReport = async (
  sessionId: string
): Promise<GetReportResponse> => {
  const response = await axiosClient.get<GetReportResponse>(
    `/sessions/${sessionId}/report`
  );
  return response.data;
};

export const exportSessionReport = async (
  sessionId: string,
  format: ReportExportFormat = 'csv'
): Promise<Blob> => {
  const response = await axiosClient.get(
    `/sessions/${sessionId}/report/export`,
    {
      params: { format },
      responseType: 'blob',
    }
  );
  return response.data;
};
