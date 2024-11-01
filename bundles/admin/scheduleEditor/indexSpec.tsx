import * as React from 'react';
import fetchMock from 'fetch-mock';
import { Provider } from 'react-redux';
import { Route, Routes } from 'react-router';
import { StaticRouter } from 'react-router-dom/server';
import configureMockStore from 'redux-mock-store';
import thunk from 'redux-thunk';
import { render, screen } from '@testing-library/react';

import ScheduleEditor from './index';

const mockStore = configureMockStore([thunk]);

describe('ScheduleEditor', () => {
  let store: ReturnType<typeof mockStore>;
  const eventId = 1;

  beforeEach(() => {
    fetchMock.restore();
    fetchMock.get('*', 404);
  });

  it('shows an error if things fail to load', () => {
    renderComponent({ status: { speedrun: 'error', event: 'error', me: 'error' } });
    expect(screen.getByText('Failed to fetch speedruns')).toBeTruthy();
  });

  function renderComponent(storeState: any) {
    store = mockStore({
      models: { ...storeState.models },
      singletons: { ...storeState.singletons },
      status: { ...storeState.status },
    });
    return render(
      <Provider store={store}>
        <StaticRouter location={`/${eventId}`}>
          <Routes>
            <Route path="/:eventId" element={<ScheduleEditor />} />
          </Routes>
        </StaticRouter>
      </Provider>,
    );
  }
});
