import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';
import eslintConfigPrettier from 'eslint-config-prettier/flat';

export default tseslint.config(
  eslint.configs.recommended,
  tseslint.configs.recommended,
  eslintConfigPrettier,
  {
    files: ['__tests__/rehearsal/**/*.{js,mjs}'],
    languageOptions: {
      globals: { process: 'readonly', setTimeout: 'readonly', clearTimeout: 'readonly', URL: 'readonly' },
    },
  },
  {
    rules: {
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/consistent-type-imports': 'error',
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
  {
    ignores: ['dist/', 'node_modules/', 'coverage/', '__tests__/**/*', '!__tests__/**/', '!__tests__/rehearsal/**/*', '__mocks__/', 'scripts/', 'lib/', 'zlibrary/'],
  },
);
