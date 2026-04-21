/// <reference types="vite/client" />
/// <reference types="unplugin-vue-router/client" />
/// <reference types="vite-plugin-vue-layouts/client" />
interface ImportMetaEnv {
    readonly VITE_API_URL: string    // 你的自定义环境变量
}

interface ImportMeta {
    readonly env: ImportMetaEnv
}