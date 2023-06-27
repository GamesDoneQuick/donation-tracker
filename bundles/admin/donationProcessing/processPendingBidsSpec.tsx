import React from 'react';
import MockAdapter from 'axios-mock-adapter';
import { Provider } from 'react-redux';
import { Route, StaticRouter } from 'react-router';
import configureMockStore from 'redux-mock-store';
import thunk from 'redux-thunk';
import { render, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import Endpoints from '@public/apiv2/Endpoints';
import HTTPUtils from '@public/apiv2/HTTPUtils';

import ProcessPendingBids from './processPendingBids';

const mockStore = configureMockStore([thunk]);

describe('ProcessPendingBids', () => {
  let store: ReturnType<typeof mockStore>;
  let subject: ReturnType<typeof renderComponent>;
  const eventId = 1;

  let mock: MockAdapter;

  beforeAll(() => {
    mock = new MockAdapter(HTTPUtils.getInstance(), { onNoMatch: 'throwException' });
  });

  beforeEach(() => {
    mock.reset();
    mock.onGet(Endpoints.BIDS(1, 'pending')).reply(200, []);
  });

  afterAll(() => {
    mock.restore();
  });

  it('loads bids on mount', () => {
    renderComponent({});
    expect(store.getActions()).toContain(jasmine.objectContaining({ type: 'MODEL_STATUS_LOADING', model: 'bid' }));
  });

  describe('when the bids have loaded', () => {
    beforeEach(() => {
      subject = renderComponent({
        models: {
          bid: [
            {
              id: 123,
              name: 'Unapproved',
              parent: 122,
            },
            {
              id: 122,
              name: 'Naming Incentive',
              allowuseroptions: true,
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

    it('has a button to approve', async () => {
      mock.onPatch(Endpoints.BID(123), { state: 'OPENED' }).replyOnce(200, {});
      userEvent.click(subject.getByText('Accept'));
      expect(mock.history.patch.length).toEqual(1);
      await waitFor(() => expect(subject.getByText('Accepted')).not.toBeNull());
    });

    it('has a button to deny', async () => {
      mock.onPatch(Endpoints.BID(123), { state: 'DENIED' }).replyOnce(200, {});
      userEvent.click(subject.getByText('Deny'));
      expect(mock.history.patch.length).toEqual(1);
      await waitFor(() => expect(subject.getByText('Denied')).not.toBeNull());
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
