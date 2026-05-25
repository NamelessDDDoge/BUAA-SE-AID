import { defineConfig, mergeConfig } from 'vitest/config'
import viteConfig from './vite.config.mts'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      globals: true,
      include: ['tests/unit/**/*.spec.ts', 'tests/integration/**/*.spec.ts', 'tests/e2e/**/*.spec.ts'],
      exclude: ['node_modules/**'],
      coverage: {
        provider: 'v8',
        reporter: ['text', 'html', 'lcov'],
        exclude: [
          'node_modules/**',
          'dist/**',
          '**/*.d.ts',
          'tests/**',
          'src/main.ts',
          'src/plugins/**',
        ],
      },
    },
  }),
)
