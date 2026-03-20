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
    '/dist/' // Ignore compiled output for test discovery
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

  // Keep global teardown if needed for force exit
  globalTeardown: '<rootDir>/jest.teardown.js',

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
      statements: 69,   // Baseline 74.74% minus ~5%
      branches: 63,     // Baseline 68.57% minus ~5%
      functions: 55,    // Baseline 60.49% minus ~5%
      lines: 71,        // Baseline 76.88% minus ~5%
    },
  },
};