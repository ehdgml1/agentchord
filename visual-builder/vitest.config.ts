import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/test/**',
        'src/**/*.test.*',
        'src/vite-env.d.ts',
        'src/types/**',
        'src/**/index.ts',
        'src/main.tsx',
        'src/data/**',
        'src/hooks/**',
        'src/components/ui/switch.tsx',
        'src/components/ui/slider.tsx',
        'src/components/ui/table.tsx',
        'src/utils/codeGenerator/types.ts',
      ],
      thresholds: {
        statements: 80,
        branches: 75,
        functions: 80,
        lines: 80,
      },
    },
  },
});
