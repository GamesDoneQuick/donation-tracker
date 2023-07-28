import React from 'react';
import fetchMock from 'fetch-mock';
import { Provider } from 'react-redux';
import { Route, StaticRouter } from 'react-router';
import configureMockStore from 'redux-mock-store';
import thunk from 'redux-thunk';
import { render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import Endpoints from '@tracker/Endpoints';

import ProcessDonations from './processDonations';

const mockStore = configureMockStore([thunk]);

describe('ProcessDonations', () => {
  let store: ReturnType<typeof mockStore>;
  let subject: ReturnType<typeof render>;
  const eventId = 1;

  beforeEach(() => {
    jasmine.clock().install();
    fetchMock.restore();
  });

  afterEach(() => {
    jasmine.clock().uninstall();
  });

  it('loads donors and donations on mount', () => {
    renderDonations({});
    jasmine.clock().tick(0);
    expect(store.getActions()).toContain(jasmine.objectContaining({ type: 'MODEL_STATUS_LOADING', model: 'donor' }));
    expect(store.getActions()).toContain(jasmine.objectContaining({ type: 'MODEL_STATUS_LOADING', model: 'donation' }));
  });

  describe('when the donations have loaded', () => {
    beforeEach(() => {
      subject = renderDonations({
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
              currency: 'USD',
              comment: 'Amazing Comment',
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
      userEvent.click(subject.getByText('Approve Comment Only'));
      expect(fetchMock.done()).toBe(true);
    });

    describe('when the user has approval powers', () => {
      beforeEach(() => {
        subject = renderDonations({
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
                currency: 'USD',
                comment: 'Amazing Comment',
                pk: 123,
              },
            ],
          },
        });
      });

      it('shows the mode dropdown', () => {
        expect(subject.getByRole('combobox')).not.toBeNull();
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
        userEvent.click(subject.queryAllByText('Send to Head')[0]);
        expect(fetchMock.done()).toBe(true);
      });

      it('has a button to send to reader when in confirm mode', () => {
        userEvent.selectOptions(subject.getByRole('combobox'), 'confirm');

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

        userEvent.click(subject.queryAllByText('Send to Reader')[0]);
        expect(fetchMock.done()).toBe(true);
      });
    });

    describe('when the user does not have approval powers', () => {
      it('does not show the mode dropdown', () => {
        expect(subject.queryByRole('combobox')).toBeNull();
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
        userEvent.click(subject.getByText('Send to Head'));
        expect(fetchMock.done()).toBe(true);
      });
    });

    describe('when one step screening is on', () => {
      beforeEach(() => {
        subject = renderDonations({
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
                currency: 'USD',
                comment: 'Amazing Comment',
                pk: 123,
              },
            ],
          },
        });
      });

      it('does not show the mode dropdown', () => {
        expect(subject.queryByRole('combobox')).toBeNull();
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
        userEvent.click(subject.getByText('Send to Reader'));
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
      userEvent.click(subject.getByText('Block Comment'));
      expect(fetchMock.done()).toBe(true);
    });
  });

  function renderDonations(storeState: any) {
    store = mockStore({
      models: { ...storeState.models },
      singletons: { ...storeState.singletons },
      status: { ...storeState.status },
    });
    return render(
      <Provider store={store}>
        <StaticRouter location={'' + eventId}>
          <Route path={':event'} component={ProcessDonations} />
        </StaticRouter>
      </Provider>,
    );
  }
});
