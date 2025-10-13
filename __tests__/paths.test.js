/**
 * Tests for Path Resolution Helpers
 *
 * Verifies that centralized path resolution works correctly
 * across different environments and use cases.
 */

import { describe, test, expect } from '@jest/globals';
import {
  getProjectRoot,
  getPythonScriptPath,
  getPythonLibDirectory,
  getPackageJsonPath,
  getRequirementsTxtPath,
  getVenvPath
} from '../dist/lib/paths.js';
import { existsSync, readFileSync } from 'fs';
import * as path from 'path';

describe('Path Resolution Helpers', () => {
  describe('getProjectRoot()', () => {
    test('should return absolute path to project root', () => {
      const root = getProjectRoot();

      expect(root).toBeTruthy();
      expect(path.isAbsolute(root)).toBe(true);
      expect(root).toContain('zlibrary-mcp');
    });

    test('project root should contain package.json', () => {
      const root = getProjectRoot();
      const pkgPath = path.join(root, 'package.json');

      expect(existsSync(pkgPath)).toBe(true);
    });

    test('project root should contain dist/ directory', () => {
      const root = getProjectRoot();
      const distPath = path.join(root, 'dist');

      expect(existsSync(distPath)).toBe(true);
    });

    test('project root should contain lib/ directory', () => {
      const root = getProjectRoot();
      const libPath = path.join(root, 'lib');

      expect(existsSync(libPath)).toBe(true);
    });
  });

  describe('getPythonScriptPath()', () => {
    test('should return path to python_bridge.py', () => {
      const scriptPath = getPythonScriptPath('python_bridge.py');

      expect(scriptPath).toBeTruthy();
      expect(scriptPath).toContain('lib');
      expect(scriptPath).toContain('python_bridge.py');
      expect(existsSync(scriptPath)).toBe(true);
    });

    test('should return path to rag_processing.py', () => {
      const scriptPath = getPythonScriptPath('rag_processing.py');

      expect(scriptPath).toContain('lib');
      expect(scriptPath).toContain('rag_processing.py');
      expect(existsSync(scriptPath)).toBe(true);
    });

    test('should handle different script names', () => {
      const scripts = [
        'python_bridge.py',
        'rag_processing.py',
        'enhanced_metadata.py',
        'client_manager.py'
      ];

      scripts.forEach(scriptName => {
        const scriptPath = getPythonScriptPath(scriptName);
        expect(scriptPath).toContain(scriptName);
        expect(existsSync(scriptPath)).toBe(true);
      });
    });
  });

  describe('getPythonLibDirectory()', () => {
    test('should return path to lib/ directory', () => {
      const libDir = getPythonLibDirectory();

      expect(libDir).toBeTruthy();
      expect(libDir).toContain('lib');
      expect(existsSync(libDir)).toBe(true);
    });

    test('lib directory should contain python_bridge.py', () => {
      const libDir = getPythonLibDirectory();
      const bridgePath = path.join(libDir, 'python_bridge.py');

      expect(existsSync(bridgePath)).toBe(true);
    });
  });

  describe('getPackageJsonPath()', () => {
    test('should return path to package.json', () => {
      const pkgPath = getPackageJsonPath();

      expect(pkgPath).toBeTruthy();
      expect(pkgPath).toContain('package.json');
      expect(existsSync(pkgPath)).toBe(true);
    });

    test('package.json should be parseable', () => {
      const pkgPath = getPackageJsonPath();
      const content = readFileSync(pkgPath, 'utf8');
      const pkg = JSON.parse(content);

      expect(pkg.name).toBe('zlibrary-mcp');
      expect(pkg.version).toBeTruthy();
    });
  });

  describe('getRequirementsTxtPath()', () => {
    test('should return path to requirements.txt', () => {
      const reqPath = getRequirementsTxtPath();

      expect(reqPath).toBeTruthy();
      expect(reqPath).toContain('requirements.txt');
      expect(existsSync(reqPath)).toBe(true);
    });
  });

  describe('getVenvPath()', () => {
    test('should return path to venv directory', () => {
      const venvPath = getVenvPath();

      expect(venvPath).toBeTruthy();
      expect(venvPath).toContain('venv');
      // Note: venv may or may not exist depending on setup
    });
  });

  describe('Path Resolution Consistency', () => {
    test('all paths should be under same project root', () => {
      const root = getProjectRoot();
      const scriptPath = getPythonScriptPath('python_bridge.py');
      const libDir = getPythonLibDirectory();
      const pkgPath = getPackageJsonPath();
      const reqPath = getRequirementsTxtPath();
      const venvPath = getVenvPath();

      expect(scriptPath).toContain(root);
      expect(libDir).toContain(root);
      expect(pkgPath).toContain(root);
      expect(reqPath).toContain(root);
      expect(venvPath).toContain(root);
    });

    test('Python script paths should be in lib directory', () => {
      const libDir = getPythonLibDirectory();
      const scriptPath = getPythonScriptPath('python_bridge.py');

      expect(scriptPath).toContain(libDir);
    });
  });
});
