import React from 'react';
import thunk from 'redux-thunk';
import configureMockStore from 'redux-mock-store';
import { mount } from 'enzyme';
import fetchMock from 'fetch-mock';
import { Provider } from 'react-redux';
import { Route, StaticRouter } from 'react-router';

import ReadDonations from './readDonations';
import Endpoints from '../../tracker/Endpoints';

const mockStore = configureMockStore([thunk]);

describe('ReadDonations', () => {
  let store: ReturnType<typeof mockStore>;
  let subject: ReturnType<typeof render>;
  const eventId = 1;

  beforeEach(() => {
    fetchMock.restore();
  });

  it('loads donors and donations on mount', () => {
    render({});
    expect(store.getActions()).toContain(jasmine.objectContaining({ type: 'MODEL_STATUS_LOADING', model: 'donor' }));
    expect(store.getActions()).toContain(jasmine.objectContaining({ type: 'MODEL_STATUS_LOADING', model: 'donation' }));
  });

  describe('when the donations have loaded', () => {
    beforeEach(() => {
      subject = render({
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
              pk: 123,
            },
          ],
        },
      });
      subject.update();
    });

    it('displays the donation info', () => {
      expect(subject.findWhere(td => td.text() === 'alias#1234')).toExist();
      expect(subject.findWhere(td => td.text() === 'Amazing Comment')).toExist();
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
      subject.findWhere(b => b.type() === 'button' && b.text() === 'Read').simulate('click');
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
      subject.findWhere(b => b.type() === 'button' && b.text() === 'Ignore').simulate('click');
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
      subject.findWhere(b => b.type() === 'button' && b.text() === 'Block Comment').simulate('click');
      expect(fetchMock.done()).toBe(true);
    });

    it('has a button to pin and unpin', () => {
      subject.findWhere(b => b.type() === 'button' && b.text() === 'Pin Comment').simulate('click');
      subject.update();
      expect(subject.findWhere(td => !!td.text().match(/📌.*Amazing Comment/))).toExist();

      subject.findWhere(b => b.type() === 'button' && b.text() === 'Unpin Comment').simulate('click');
      subject.update();
      expect(subject.findWhere(td => td.text() === 'Amazing Comment')).toExist();
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
        <StaticRouter location={'' + eventId}>
          <Route path={':event'} component={ReadDonations} />
        </StaticRouter>
      </Provider>,
    );
  }
});
