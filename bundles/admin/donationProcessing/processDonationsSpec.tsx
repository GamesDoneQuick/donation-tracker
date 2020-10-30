import React from 'react';
import thunk from 'redux-thunk';
import configureMockStore from 'redux-mock-store';
import { mount } from 'enzyme';
import fetchMock from 'fetch-mock';
import { Provider } from 'react-redux';
import { Route, StaticRouter } from 'react-router';

import ProcessDonations from './processDonations';
import Endpoints from '../../tracker/Endpoints';

const mockStore = configureMockStore([thunk]);

describe('ProcessDonations', () => {
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

    it('has a button to approve', () => {
      fetchMock.postOnce(
        Endpoints.EDIT,
        {
          body: [],
        },
        {
          functionMatcher: (url, request) => {
            return request.body === 'commentstate=APPROVED&id=123&readstate=IGNORED&type=donation';
          },
        },
      );
      subject.findWhere(b => b.type() === 'button' && b.text() === 'Approve Comment Only').simulate('click');
      expect(fetchMock.done()).toBe(true);
    });

    describe('when the user has approval powers', () => {
      beforeEach(() => {
        subject = render({
          singletons: {
            me: {
              staff: true,
              permissions: ['tracker.send_to_reader'],
            },
          },
          models: {
            donor: [
              {
                alias: 'alias',
                alias_no: 1234,
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
      });

      it('shows the mode dropdown', () => {
        expect(subject.find('select')).toExist();
      });

      it('has a button to send to head when in normal mode', () => {
        fetchMock.postOnce(
          Endpoints.EDIT,
          {
            body: [],
          },
          {
            functionMatcher: (url, request) => {
              return request.body === 'commentstate=APPROVED&id=123&readstate=FLAGGED&type=donation';
            },
          },
        );
        subject.findWhere(b => b.type() === 'button' && b.text() === 'Send to Head').simulate('click');
        expect(fetchMock.done()).toBe(true);
      });

      it('has a button to send to reader when in confirm mode', () => {
        subject.find('select').simulate('change', { target: { value: 'confirm' } });
        subject.update();

        fetchMock.postOnce(
          Endpoints.EDIT,
          {
            body: [],
          },
          {
            functionMatcher: (url, request) => {
              return request.body === 'commentstate=APPROVED&id=123&readstate=READY&type=donation';
            },
          },
        );
        subject.findWhere(b => b.type() === 'button' && b.text() === 'Send to Reader').simulate('click');
        expect(fetchMock.done()).toBe(true);
      });
    });

    describe('when the user does not have approval powers', () => {
      it('does not show the mode dropdown', () => {
        expect(subject.find('select')).not.toExist();
      });

      it('has a button to send to head', () => {
        fetchMock.postOnce(
          Endpoints.EDIT,
          {
            body: [],
          },
          {
            functionMatcher: (url, request) => {
              return request.body === 'commentstate=APPROVED&id=123&readstate=FLAGGED&type=donation';
            },
          },
        );
        subject.findWhere(b => b.type() === 'button' && b.text() === 'Send to Head').simulate('click');
        expect(fetchMock.done()).toBe(true);
      });
    });

    describe('when one step screening is on', () => {
      beforeEach(() => {
        subject = render({
          models: {
            event: [
              {
                use_one_step_screening: true,
                pk: eventId,
              },
            ],
            donor: [
              {
                alias: 'alias',
                alias_no: 1234,
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
      });

      it('does not show the mode dropdown', () => {
        expect(subject.find('select')).not.toExist();
      });

      it('has a button to send to reader', () => {
        fetchMock.postOnce(
          Endpoints.EDIT,
          {
            body: [],
          },
          {
            functionMatcher: (url, request) => {
              return request.body === 'commentstate=APPROVED&id=123&readstate=READY&type=donation';
            },
          },
        );
        subject.findWhere(b => b.type() === 'button' && b.text() === 'Send to Reader').simulate('click');
        expect(fetchMock.done()).toBe(true);
      });
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
          <Route path={':event'} component={ProcessDonations} />
        </StaticRouter>
      </Provider>,
    );
  }
});
