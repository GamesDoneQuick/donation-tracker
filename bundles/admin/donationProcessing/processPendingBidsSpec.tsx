import React from 'react';
import MockAdapter from 'axios-mock-adapter';
import { Provider } from 'react-redux';
import { Route } from 'react-router';
import { Routes } from 'react-router-dom';
import { StaticRouter } from 'react-router-dom/server';
import { act, cleanup, queryByAttribute, render, waitForElementToBeRemoved } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { APIEvent, Me, PaginationInfo } from '@public/apiv2/APITypes';
import Endpoints from '@public/apiv2/Endpoints';
import HTTPUtils from '@public/apiv2/HTTPUtils';
import { apiRootSlice, trackerApi } from '@public/apiv2/reducers/trackerApi';
import { store } from '@public/apiv2/Store';

import ProcessPendingBids from './processPendingBids';

describe('ProcessPendingBids', () => {
  let subject: ReturnType<typeof render>;
  const eventId = 1;

  let mock: MockAdapter;
  let me: Me;

  async function waitForSpinner() {
    function spinner() {
      return queryByAttribute('data-test-id', subject.baseElement, 'spinner');
    }

    if (spinner()) {
      await waitForElementToBeRemoved(spinner);
    }
  }

  beforeAll(() => {
    mock = new MockAdapter(HTTPUtils.getInstance(), { onNoMatch: 'throwException' });
  });

  beforeEach(() => {
    store.dispatch(apiRootSlice.actions.setRoot({ root: '//testserver/', limit: 500, csrfToken: 'deadbeef' }));
    mock.reset();
    me = {
      username: 'test',
      staff: true,
      superuser: false,
      permissions: [],
    };
    const events: PaginationInfo<APIEvent> = {
      count: 1,
      previous: null,
      next: null,
      results: [
        {
          type: 'event',
          id: 1,
          name: 'Test',
          short: 'Test',
          hashtag: 'test',
          datetime: '2025-01-05T11:30:00-05:00',
          timezone: 'US/Eastern',
          receivername: 'Charity',
          receiver_short: 'C',
          receiver_logo: '',
          receiver_privacy_policy: '',
          receiver_solicitation_text: '',
          paypalcurrency: 'USD',
          use_one_step_screening: true,
          allow_donations: true,
          locked: false,
        },
      ],
    };
    mock.onGet('//testserver/' + Endpoints.ME).reply(() => [200, me]);
    mock.onGet('//testserver/' + Endpoints.EVENTS).reply(200, events);
    mock.onGet('//testserver/' + Endpoints.BIDS({ eventId, feed: 'pending', tree: true })).reply(200, {
      count: 1,
      previous: null,
      next: null,
      results: [
        {
          id: 122,
          name: 'Naming Incentive',
          allowuseroptions: true,
          option_max_length: 12,
          options: [
            {
              id: 123,
              name: 'Unapproved',
              state: 'PENDING',
            },
          ],
        },
      ],
    });
  });

  afterEach(() => {
    cleanup();
  });

  afterAll(() => {
    mock.restore();
  });

  it('loads bids on mount', async () => {
    await renderComponent();
    expect(trackerApi.util.selectCachedArgsForQuery(store.getState(), 'bidTree')).toContain({
      urlParams: { eventId, feed: 'pending' },
    });
  });

  describe('when the bids have loaded', () => {
    beforeEach(async () => {
      await renderComponent();
    });

    it('displays the bid/parent info', () => {
      expect(subject.getByText('Unapproved')).not.toBeNull();
      expect(subject.getByText(text => text.includes('Naming Incentive'))).not.toBeNull();
      expect(subject.getByText(text => text.includes('Max Option Length: 12'))).not.toBeNull();
    });

    it('does not show accept or deny with no user permissions', () => {
      expect(subject.queryByText('Accept')).toBeNull();
      expect(subject.queryByText('Deny')).toBeNull();
    });

    describe('when the user has permission', () => {
      beforeEach(async () => {
        me.permissions = ['tracker.approve_bid'];
        await renderComponent();
      });

      it('has a button to approve', async () => {
        mock.onPatch(Endpoints.APPROVE_BID(123)).replyOnce(200, {});
        expect(subject.getByText(/Pending/)).not.toBeNull();
        userEvent.click(subject.getByText('Accept'));
        expect(mock.history.patch.length).toEqual(1);
        await waitForElementToBeRemoved(() => queryByAttribute('data-test-id', subject.baseElement, 'spinner'));
        expect(subject.queryByText(/Pending/)).toBeNull();
        expect(subject.getByText(/Accepted/)).not.toBeNull();
      });

      it('has a button to deny', async () => {
        mock.onPatch(Endpoints.DENY_BID(123)).replyOnce(200, {});
        expect(subject.getByText(/Pending/)).not.toBeNull();
        userEvent.click(subject.getByText('Deny'));
        expect(mock.history.patch.length).toEqual(1);
        await waitForElementToBeRemoved(() => queryByAttribute('data-test-id', subject.baseElement, 'spinner'));
        expect(subject.queryByText(/Pending/)).toBeNull();
        expect(subject.getByText(/Denied/)).not.toBeNull();
      });
    });
  });

  async function renderComponent() {
    act(() => {
      store.dispatch(trackerApi.util.resetApiState());
    });
    cleanup();
    subject = render(
      <Provider store={store}>
        <StaticRouter location={`/${eventId}`}>
          <Routes>
            <Route path="/:eventId" element={<ProcessPendingBids />} />
          </Routes>
        </StaticRouter>
      </Provider>,
    );

    await waitForSpinner();
  }
});
