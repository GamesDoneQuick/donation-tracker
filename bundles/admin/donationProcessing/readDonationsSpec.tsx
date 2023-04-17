import React from 'react';
import fetchMock from 'fetch-mock';
import { Provider } from 'react-redux';
import { Route, StaticRouter } from 'react-router';
import configureMockStore from 'redux-mock-store';
import thunk from 'redux-thunk';
import { render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import Endpoints from '@tracker/Endpoints';

import ReadDonations from './readDonations';

const mockStore = configureMockStore([thunk]);

describe('ReadDonations', () => {
  let store: ReturnType<typeof mockStore>;
  let subject: ReturnType<typeof renderComponent>;
  const eventId = 1;

  beforeEach(() => {
    jasmine.clock().install();
    fetchMock.restore();
  });

  afterEach(() => {
    jasmine.clock().uninstall();
  });

  it('loads donors and donations on mount', () => {
    renderComponent({});
    jasmine.clock().tick(0);
    expect(store.getActions()).toContain(jasmine.objectContaining({ type: 'MODEL_STATUS_LOADING', model: 'donor' }));
    expect(store.getActions()).toContain(jasmine.objectContaining({ type: 'MODEL_STATUS_LOADING', model: 'donation' }));
  });

  describe('when the donations have loaded', () => {
    beforeEach(() => {
      subject = renderComponent({
        models: {
          donor: [
            {
              alias: 'alias',
              alias_num: 1234,
              pk: 1,
            },
          ],
          donation: [
            {
              donor: 1,
              amount: 164.87,
              comment: 'Amazing Comment',
              pinned: false,
              pk: 123,
            },
          ],
        },
      });
    });

    it('displays the donation info', () => {
      expect(subject.getByText('alias#1234')).not.toBeNull();
      expect(subject.getByText('Amazing Comment')).not.toBeNull();
    });

    it('has a button to mark as read', () => {
      fetchMock.postOnce(
        Endpoints.EDIT,
        {
          body: [],
        },
        {
          functionMatcher: (url, request) => {
            return request.body === 'id=123&readstate=READ&type=donation';
          },
        },
      );
      userEvent.click(subject.getByText('Read'));
      expect(fetchMock.done()).toBe(true);
    });

    it('has a button to mark as ignored', () => {
      fetchMock.postOnce(
        Endpoints.EDIT,
        {
          body: [],
        },
        {
          functionMatcher: (url, request) => {
            return request.body === 'id=123&readstate=IGNORED&type=donation';
          },
        },
      );
      userEvent.click(subject.getByText('Ignore'));
      expect(fetchMock.done()).toBe(true);
    });

    it('has a button to block', () => {
      fetchMock.postOnce(
        Endpoints.EDIT,
        {
          body: [],
        },
        {
          functionMatcher: (url, request) => {
            return request.body === 'commentstate=DENIED&id=123&readstate=IGNORED&type=donation';
          },
        },
      );
      userEvent.click(subject.getByText('Block Comment'));
      expect(fetchMock.done()).toBe(true);
    });

    it('has a button to pin', () => {
      fetchMock.postOnce(
        Endpoints.EDIT,
        {
          body: [],
        },
        {
          functionMatcher: (url, request) => {
            return request.body === 'id=123&pinned=1&type=donation';
          },
        },
      );
      userEvent.click(subject.getByText('Pin Comment'));
      expect(fetchMock.done()).toBe(true);
    });

    it('has a button to unpin', () => {
      subject = renderComponent({
        models: {
          donor: [
            {
              alias: 'alias',
              alias_num: 1234,
              pk: 1,
            },
          ],
          donation: [
            {
              donor: 1,
              amount: 164.87,
              comment: 'Amazing Comment',
              pinned: true,
              pk: 123,
            },
          ],
        },
      });
      fetchMock.postOnce(
        Endpoints.EDIT,
        {
          body: [],
        },
        {
          functionMatcher: (url, request) => {
            return request.body === 'id=123&pinned=0&type=donation';
          },
        },
      );
      userEvent.click(subject.getByText('Unpin Comment'));
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
        <StaticRouter location={'' + eventId}>
          <Route path={':event'} component={ReadDonations} />
        </StaticRouter>
      </Provider>,
    );
  }
});
