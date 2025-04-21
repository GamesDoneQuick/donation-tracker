import React from 'react';
import MockAdapter from 'axios-mock-adapter';
import { Provider } from 'react-redux';
import { Route } from 'react-router';
import { Routes } from 'react-router-dom';
import { StaticRouter } from 'react-router-dom/server';
import { act, cleanup, render, waitForElementToBeRemoved, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { findChildInTree, Me } from '@public/apiv2/APITypes';
import Endpoints from '@public/apiv2/Endpoints';
import HTTPUtils from '@public/apiv2/HTTPUtils';
import { setRoot } from '@public/apiv2/reducers/apiRoot';
import { trackerApi } from '@public/apiv2/reducers/trackerApi';
import { BidQuery } from '@public/apiv2/reducers/trackerBaseApi';
import { store } from '@public/apiv2/Store';

import { getFixtureMixedBidsTree } from '@spec/fixtures/bid';
import { getFixturePagedEvent } from '@spec/fixtures/event';
import { waitForSpinner } from '@spec/helpers/rtl';

import ProcessPendingBids from './processPendingBids';

describe('ProcessPendingBids', () => {
  let subject: ReturnType<typeof render>;
  const eventId = 1;

  let mock: MockAdapter;
  let me: Me;

  const params: BidQuery = { urlParams: { eventId, feed: 'pending', tree: true } };

  function actualParams() {
    expect(typeof params.urlParams).not.toBe('number');
    // @ts-expect-error I AM NOT A NUMBER
    const { tree, ...urlParams } = params.urlParams;
    expect(tree).toBeTrue();
    return { ...params, urlParams };
  }

  function treeParams(params: BidQuery['urlParams']) {
    if (typeof params === 'number') {
      return { eventId: params, tree: true };
    } else {
      return {
        ...params,
        tree: true,
      };
    }
  }

  beforeAll(() => {
    mock = new MockAdapter(HTTPUtils.getInstance(), { onNoMatch: 'throwException' });
  });

  beforeEach(() => {
    store.dispatch(setRoot({ root: 'http://testserver/', limit: 500, csrfToken: 'deadbeef' }));
    mock.reset();
    me = {
      username: 'test',
      staff: true,
      superuser: false,
      permissions: [],
    };
    mock.onGet('http://testserver/' + Endpoints.ME).reply(() => [200, me]);
    mock.onGet('http://testserver/' + Endpoints.EVENTS).reply(200, getFixturePagedEvent());
    mock
      .onGet('http://testserver/' + Endpoints.BIDS(treeParams(params.urlParams)))
      .reply(200, getFixtureMixedBidsTree());
  });

  afterAll(() => {
    mock.restore();
  });

  it('loads bids on mount', async () => {
    await renderComponent();
    expect(trackerApi.util.selectCachedArgsForQuery(store.getState(), 'bidTree')).toContain(actualParams());
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
      let bidId: number;
      beforeEach(async () => {
        me.permissions = ['tracker.approve_bid'];
        await renderComponent();
        const tree = trackerApi.endpoints.bidTree.select(actualParams())(store.getState()).data;
        expect(tree).withContext('tree did not exist').toBeDefined();
        const pendingId = findChildInTree(tree ?? [], o => o.state === 'PENDING')?.id;
        expect(pendingId).withContext('pending child could not be found').toBeDefined();
        bidId = pendingId ?? 0;
      });

      it('has a button to approve', async () => {
        const row = within(subject.getByTestId(`bid-${bidId}`));
        mock.onPatch(Endpoints.APPROVE_BID(bidId)).replyOnce(200, {});
        expect(row.getByText(/Pending/)).not.toBeNull();
        userEvent.click(row.getByText('Accept'));
        expect(mock.history.patch.length).toEqual(1);
        await waitForElementToBeRemoved(() => subject.queryByTestId('state-SAVING'));
        expect(row.queryByText(/Pending/)).toBeNull();
        expect(row.getByText(/Accepted/)).not.toBeNull();
      });

      it('has a button to deny', async () => {
        const row = within(subject.getByTestId(`bid-${bidId}`));
        mock.onPatch(Endpoints.DENY_BID(bidId)).replyOnce(200, {});
        expect(row.getByText(/Pending/)).not.toBeNull();
        userEvent.click(row.getByText('Deny'));
        expect(mock.history.patch.length).toEqual(1);
        await waitForElementToBeRemoved(() => subject.queryByTestId('state-SAVING'));
        expect(row.queryByText(/Pending/)).toBeNull();
        expect(row.getByText(/Denied/)).not.toBeNull();
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
