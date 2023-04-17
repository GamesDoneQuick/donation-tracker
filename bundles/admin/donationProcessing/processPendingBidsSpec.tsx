import React from 'react';
import fetchMock from 'fetch-mock';
import { Provider } from 'react-redux';
import { Route, StaticRouter } from 'react-router';
import configureMockStore from 'redux-mock-store';
import thunk from 'redux-thunk';
import { render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import Endpoints from '@tracker/Endpoints';

import ProcessPendingBids from './processPendingBids';

const mockStore = configureMockStore([thunk]);

describe('ProcessPendingBids', () => {
  let store: ReturnType<typeof mockStore>;
  let subject: ReturnType<typeof renderComponent>;
  const eventId = 1;

  beforeEach(() => {
    fetchMock.restore();
  });

  it('loads bids on mount', () => {
    renderComponent({});
    expect(store.getActions()).toContain(
      jasmine.objectContaining({ type: 'MODEL_STATUS_LOADING', model: 'bidtarget' }),
    );
  });

  describe('when the bids have loaded', () => {
    beforeEach(() => {
      subject = renderComponent({
        models: {
          bid: [
            {
              pk: 123,
              name: 'Unapproved',
              parent: 122,
            },
            {
              pk: 122,
              public: 'Naming Incentive',
              option_max_length: 12,
            },
          ],
        },
      });
    });

    it('displays the bid/parent info', () => {
      expect(subject.getByText('Unapproved')).not.toBeNull();
      expect(subject.getByText(text => text.includes('Naming Incentive'))).not.toBeNull();
      expect(subject.getByText(text => text.includes('Max Option Length: 12'))).not.toBeNull();
    });

    it('has a button to approve', () => {
      fetchMock.postOnce(
        Endpoints.EDIT,
        {
          body: [],
        },
        {
          functionMatcher: (url, request) => {
            return request.body === 'id=123&state=OPENED&type=bid';
          },
        },
      );
      userEvent.click(subject.getByText('Accept'));
      expect(fetchMock.done()).toBe(true);
    });

    it('has a button to deny', () => {
      fetchMock.postOnce(
        Endpoints.EDIT,
        {
          body: [],
        },
        {
          functionMatcher: (url, request) => {
            return request.body === 'id=123&state=DENIED&type=bid';
          },
        },
      );
      userEvent.click(subject.getByText('Deny'));
      expect(fetchMock.done()).toBe(true);
    });
  });

  function renderComponent(storeState: any) {
    store = mockStore({
      models: { ...storeState.models },
      singletons: { ...storeState.singletons },
      status: { ...storeState.status },
    });
    return render(
      <Provider store={store}>
        <StaticRouter location={`${eventId}`}>
          <Route path={':event'} component={ProcessPendingBids} />
        </StaticRouter>
      </Provider>,
    );
  }
});
