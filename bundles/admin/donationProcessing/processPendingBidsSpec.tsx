import React from 'react';
import MockAdapter from 'axios-mock-adapter';
import { Provider } from 'react-redux';
import { Route } from 'react-router';
import { Routes } from 'react-router-dom';
import { StaticRouter } from 'react-router-dom/server';
import { act, cleanup, queryByAttribute, render, waitForElementToBeRemoved } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { Me } from '@public/apiv2/APITypes';
import Endpoints from '@public/apiv2/Endpoints';
import HTTPUtils from '@public/apiv2/HTTPUtils';
import { setRoot } from '@public/apiv2/reducers/apiRoot';
import { trackerApi } from '@public/apiv2/reducers/trackerApi';
import { store } from '@public/apiv2/Store';

import { getFixturePendingBidTree } from '@spec/fixtures/bid';
import { getFixturePagedEvent } from '@spec/fixtures/event';
import { waitForSpinner } from '@spec/helpers/rtl';

import ProcessPendingBids from './processPendingBids';

describe('ProcessPendingBids', () => {
  let subject: ReturnType<typeof render>;
  const eventId = 1;

  let mock: MockAdapter;
  let me: Me;

  beforeAll(() => {
    mock = new MockAdapter(HTTPUtils.getInstance(), { onNoMatch: 'throwException' });
  });

  beforeEach(() => {
    store.dispatch(setRoot({ root: '//testserver/', limit: 500, csrfToken: 'deadbeef' }));
    mock.reset();
    me = {
      username: 'test',
      staff: true,
      superuser: false,
      permissions: [],
    };
    mock.onGet('//testserver/' + Endpoints.ME).reply(() => [200, me]);
    mock.onGet('//testserver/' + Endpoints.EVENTS).reply(200, getFixturePagedEvent());
    mock
      .onGet('//testserver/' + Endpoints.BIDS({ eventId, feed: 'pending', tree: true }))
      .reply(200, getFixturePendingBidTree());
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
        await waitForElementToBeRemoved(() => queryByAttribute('data-test-state', subject.baseElement, 'SAVING'));
        expect(subject.queryByText(/Pending/)).toBeNull();
        expect(subject.getByText(/Accepted/)).not.toBeNull();
      });

      it('has a button to deny', async () => {
        mock.onPatch(Endpoints.DENY_BID(123)).replyOnce(200, {});
        expect(subject.getByText(/Pending/)).not.toBeNull();
        userEvent.click(subject.getByText('Deny'));
        expect(mock.history.patch.length).toEqual(1);
        await waitForElementToBeRemoved(() => queryByAttribute('data-test-state', subject.baseElement, 'SAVING'));
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

    await waitForSpinner(subject);
  }
});
