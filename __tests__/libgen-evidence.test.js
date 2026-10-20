import { expect, test } from '@jest/globals';
import { AcquisitionTools } from '../dist/lib/acquisition-tools.js';

test.each(['book', 'article'])('get_book keeps LibGen %s type evidence internal', async (type) => {
  const tools = new AcquisitionTools(
    async () => ({
      books: [
        {
          title: 'The Inner Citadel',
          md5: 'e3f85ebc6faa062bceb95b349f369672',
          language: 'English',
          source: 'libgen',
          content_type: type,
        },
      ],
    }),
    {},
  );
  const search = await tools.call('search', { query: 'inner citadel', sources: ['libgen'] });
  const details = await tools.call('get_book', { ref: search.rows[0].ref });

  expect(details.evidence.search).toEqual(['title', 'md5', 'language', 'source']);
  expect(details.identifiers.md5).toBe('e3f85ebc6faa062bceb95b349f369672');
  expect(JSON.stringify({ search, details })).not.toContain('content_type');
});
