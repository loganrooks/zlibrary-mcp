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

  // Removed for simplification:
  // collectCoverage, collectCoverageFrom, coverageDirectory, coverageReporters
  // transformIgnorePatterns (was already commented out)
  // testTimeout
  // clearMocks (handled inside tests now)
};