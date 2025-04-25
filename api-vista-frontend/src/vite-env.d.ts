/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  // other env vars...
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
