import React from 'react';
import MockAdapter from 'axios-mock-adapter';
import { render } from '@testing-library/react';

import HTTPUtils, { request, resetPrefetch } from '@public/apiv2/HTTPUtils';

import APIPrefetch from '@spec/components/APIPrefetch';

describe('HTTPUtils', () => {
  let mock: MockAdapter;

  beforeAll(() => {
    mock = new MockAdapter(HTTPUtils.getInstance());
  });

  beforeEach(() => {
    mock.reset();
  });

  afterAll(() => {
    mock.restore();
  });

  describe('prefetch', () => {
    afterEach(() => {
      resetPrefetch();
    });

    it('uses the prefetch in the document once', async () => {
      render(<APIPrefetch data={{ 'test/path': { foo: 'bar' } }} />);
      const result = await request<{ foo: 'bar' }>({ url: 'test/path' });
      expect(result.data.foo).toBe('bar');
      expect(mock.history.get.length).toBe(0);

      // second time
      await expectAsync(request({ url: 'test/path' })).toBeRejected();
      expect(mock.history.get.length).toBe(1);

      // not in the prefetch
      await expectAsync(request({ url: 'other/path' })).toBeRejected();
      expect(mock.history.get.length).toBe(2);
    });
  });
});
