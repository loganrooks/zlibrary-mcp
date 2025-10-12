// jest.teardown.js
// Convert to ESM syntax
export default async () => {
  console.log('Forcing Jest to exit via globalTeardown...');
  process.exit(0);
};