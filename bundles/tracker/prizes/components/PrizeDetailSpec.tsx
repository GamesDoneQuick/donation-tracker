import React from 'react';
import MockAdapter from 'axios-mock-adapter';
import { Provider } from 'react-redux';
import { Route, Routes } from 'react-router';
import { StaticRouter } from 'react-router-dom/server';
import { act, cleanup, fireEvent, render } from '@testing-library/react';

import Endpoints from '@public/apiv2/Endpoints';
import HTTPUtils from '@public/apiv2/HTTPUtils';
import { setRoot } from '@public/apiv2/reducers/apiRoot';
import { trackerApi } from '@public/apiv2/reducers/trackerApi';
import { store } from '@public/apiv2/Store';

import { getFixturePagedEvent } from '@spec/fixtures/event';
import { getFixturePagedPrizes } from '@spec/fixtures/Prize';
import { getFixturePagedRuns } from '@spec/fixtures/run';
import { waitForSpinner } from '@spec/helpers/rtl';

import PrizeDetail from './PrizeDetail';

describe('PrizeDetail', () => {
  let subject: ReturnType<typeof render>;

  let mock: MockAdapter;
  const eventId = 1;

  beforeAll(() => {
    mock = new MockAdapter(HTTPUtils.getInstance(), { onNoMatch: 'throwException' });
  });

  beforeEach(() => {
    store.dispatch(setRoot({ root: '//testserver/', limit: 500, csrfToken: 'deadbeef' }));
    mock.reset();
    mock.onGet('//testserver/' + Endpoints.EVENTS).reply(200, getFixturePagedEvent({ id: eventId }));
    mock.onGet('//testserver/' + Endpoints.PRIZES(eventId)).reply(200, getFixturePagedPrizes());
    mock.onGet('//testserver/' + Endpoints.RUNS(eventId)).reply(200, getFixturePagedRuns());
  });

  it('displays "No Image Found" if an error occurs while loading the image', async () => {
    await renderComponent();

    fireEvent.error(await subject.findByRole('img'));
    expect(subject.queryByRole('img')).toBeNull();
    expect(subject.getByText('No Image Provided')).not.toBeNull();
  });

  afterEach(() => {
    cleanup();
  });

  afterAll(() => {
    mock.restore();
  });

  async function renderComponent(props?: Partial<React.ComponentProps<typeof PrizeDetail>>) {
    const defaultProps = {
      prizeId: 123,
    };

    act(() => {
      store.dispatch(trackerApi.util.resetApiState());
    });

    cleanup();
    subject = render(
      <Provider store={store}>
        <StaticRouter location={`/1`}>
          <Routes>
            <Route path="/:eventId" element={<PrizeDetail {...defaultProps} {...props} />} />
          </Routes>
        </StaticRouter>
      </Provider>,
    );

    await waitForSpinner(subject);
  }
});
