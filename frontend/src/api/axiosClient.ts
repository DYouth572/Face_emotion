import axios, {
  AxiosInstance,
  AxiosError,
  InternalAxiosRequestConfig,
  AxiosResponse,
} from 'axios';
import { API_BASE_URL } from '@/utils/constants';
import type { ApiErrorResponse } from '@/types/api.types';

const axiosClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

axiosClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => config,
  (error: AxiosError) => Promise.reject(error)
);

axiosClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError<ApiErrorResponse>) => {
    const status = error.response?.status;
    const message = error.response?.data?.message ?? error.message;

    if (status === 404) {
      console.warn('[API] 404 Not Found:', error.config?.url);
    } else if (status === 500) {
      console.error('[API] Server Error:', message);
    } else if (!error.response) {
      console.error('[API] Network Error - Backend không phản hồi');
    }

    return Promise.reject(error);
  }
);

export default axiosClient;
