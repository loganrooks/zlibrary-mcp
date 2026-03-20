// Simplified jest.config.js for ESM troubleshooting
import { createDefaultEsmPreset } from 'ts-jest';

const preset = createDefaultEsmPreset();

export default {
  // Apply the ts-jest ESM preset
  ...preset,

  // Basic Node environment
  testEnvironment: 'node',

  // Match test files in __tests__
  testMatch: [
    '**/__tests__/**/*.test.js' // Assuming tests remain JS files
  ],

  // Ignore node_modules and dist (except for moduleNameMapper resolution)
  testPathIgnorePatterns: [
    '/node_modules/',
    '/dist/', // Ignore compiled output for test discovery
    '/__tests__/e2e/', // E2E tests require running Docker container
    '/__tests__/integration/' // Integration tests require live services
  ],

  // Crucial: Map imports from __tests__ to compiled dist/ files
  moduleNameMapper: {
    // Add preset's moduleNameMapper first
    ...preset.moduleNameMapper,
    // Map relative paths from __tests__ to the compiled files in dist/
    // Match imports like '../lib/module.js' from '__tests__/...'
    '^../lib/(.*)\\.js$': '<rootDir>/dist/lib/$1.js',
    // Match imports like '../index.js' or '../dist/index.js' from '__tests__/...'
    '^../(dist/)?index\\.js$': '<rootDir>/dist/index.js',
    // Keep the SDK mock if still needed, otherwise remove
    // '^@modelcontextprotocol/server$': '<rootDir>/__mocks__/@modelcontextprotocol/server.js',
  },

  // Use --forceExit in test script instead of globalTeardown
  // (globalTeardown's process.exit(0) masks coverage threshold failures)

  // Explicitly disable transformations to prevent Jest from interfering with ESM
  transform: {},

  // Coverage configuration
  collectCoverage: true,
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'json-summary'],
  collectCoverageFrom: [
    'dist/**/*.js',
    '!dist/**/*.test.js',
    '!dist/**/*.d.ts',
  ],
  coverageThreshold: {
    global: {
      statements: 66,   // Baseline 71.16% minus ~5% (93-test suite)
      branches: 56,     // Baseline 60.99% minus ~5% (93-test suite)
      functions: 48,    // Baseline 53.08% minus ~5% (93-test suite)
      lines: 68,        // Baseline 73.17% minus ~5% (93-test suite)
    },
  },
};