import React from 'react';
import thunk from 'redux-thunk';
import configureMockStore from 'redux-mock-store';
import { mount } from 'enzyme';
import fetchMock from 'fetch-mock';
import { Provider } from 'react-redux';
import { Route, StaticRouter } from 'react-router';

import Endpoints from '@tracker/Endpoints';
import ProcessPendingBids from './processPendingBids';

const mockStore = configureMockStore([thunk]);

describe('ProcessPendingBids', () => {
  let store: ReturnType<typeof mockStore>;
  let subject: ReturnType<typeof render>;
  const eventId = 1;

  beforeEach(() => {
    fetchMock.restore();
  });

  it('loads bids on mount', () => {
    render({});
    expect(store.getActions()).toContain(
      jasmine.objectContaining({ type: 'MODEL_STATUS_LOADING', model: 'bidtarget' }),
    );
  });

  describe('when the bids have loaded', () => {
    beforeEach(() => {
      subject = render({
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
      subject.update();
    });

    it('displays the bid/parent info', () => {
      expect(subject.findWhere(td => td.text() === 'Unapproved')).toExist();
      expect(subject.findWhere(td => td.text().includes('Naming Incentive'))).toExist();
      expect(subject.findWhere(td => td.text().includes('Max Option Length: 12'))).toExist();
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
      subject.findWhere(b => b.type() === 'button' && b.text() === 'Accept').simulate('click');
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
      subject.findWhere(b => b.type() === 'button' && b.text() === 'Deny').simulate('click');
      expect(fetchMock.done()).toBe(true);
    });
  });

  function render(storeState: any) {
    store = mockStore({
      models: { ...storeState.models },
      singletons: { ...storeState.singletons },
      status: { ...storeState.status },
    });
    return mount(
      <Provider store={store}>
        <StaticRouter location={`${eventId}`}>
          <Route path={':event'} component={ProcessPendingBids} />
        </StaticRouter>
      </Provider>,
    );
  }
});
