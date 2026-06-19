/// <reference types="vite/client" />

// ===== Khai báo module CSS =====
declare module '*.css' {
  const content: Record<string, string>;
  export default content;
}

// ===== Khai báo biến môi trường =====
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_WS_URL: string;
  readonly VITE_APP_NAME: string;
  readonly VITE_APP_VERSION: string;
  readonly VITE_ENABLE_DEBUG?: string;
  readonly VITE_ENABLE_MOCK?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
