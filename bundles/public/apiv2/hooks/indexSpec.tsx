import React from 'react';
import MockAdapter from 'axios-mock-adapter';
import { Provider } from 'react-redux';
import { Route, Routes } from 'react-router';
import { StaticRouter } from 'react-router-dom/server';
import { act, render } from '@testing-library/react';

import { Permission } from '@common/Permissions';
import APIErrorList from '@public/APIErrorList';
import Endpoints from '@public/apiv2/Endpoints';
import HTTPUtils from '@public/apiv2/HTTPUtils';
import { Event, Me } from '@public/apiv2/Models';
import { processEvent } from '@public/apiv2/Processors';
import { setRoot } from '@public/apiv2/reducers/apiRoot';
import { trackerApi } from '@public/apiv2/reducers/trackerApi';
import { RootState, store } from '@public/apiv2/Store';

import { getFixturePagedDonations } from '@spec/fixtures/donation';
import { getFixtureEvent, getFixturePagedEvent } from '@spec/fixtures/event';

import { useArchivedPermission, useDonation, useDonationsQuery, usePermission } from './index';

describe('api hooks', () => {
  let subject: ReturnType<typeof render>;
  let mock: MockAdapter;

  beforeAll(() => {
    mock = new MockAdapter(HTTPUtils.getInstance(), { onNoMatch: 'throwException' });
  });

  beforeEach(() => {
    store.dispatch(setRoot({ root: '//testserver/', limit: 500, csrfToken: 'deadbeef' }));
    store.dispatch(trackerApi.util.resetApiState());
    mock.reset();
  });

  afterAll(() => {
    mock.restore();
  });

  describe('auth helpers', () => {
    describe('usePermission', () => {
      it('returns true if the user exists, is staff, and is a superuser', async () => {
        await renderComponent(
          { username: 'super', staff: true, superuser: true, permissions: [] },
          'tracker.view_event',
        );
        expect(subject.getByText('true')).not.toBeNull();
      });

      it('returns true if the user exists, is staff, and has the permission in their list', async () => {
        await renderComponent(
          { username: 'staff', staff: true, superuser: false, permissions: ['tracker.view_event'] },
          'tracker.view_event',
        );
        expect(subject.getByText('true')).not.toBeNull();
      });

      it('returns false if the user exists, is staff, but does not have the permission', async () => {
        await renderComponent(
          { username: 'staff', staff: true, superuser: false, permissions: ['tracker.view_event'] },
          'tracker.view_ad',
        );
        expect(subject.getByText('false')).not.toBeNull();
      });

      it('returns false if the user exists and has the permission but is not staff', async () => {
        await renderComponent(
          { username: 'user', staff: false, superuser: false, permissions: ['tracker.view_event'] },
          'tracker.view_event',
        );
        expect(subject.getByText('false')).not.toBeNull();
      });

      it('returns false if Me cannot be retrieved', async () => {
        await renderComponent(null, 'tracker.view_event');
        expect(subject.getByText('false')).not.toBeNull();
      });

      async function renderComponent(me: Me | null, ...permissions: Permission[]) {
        if (me != null) {
          mock.onGet('//testserver/' + Endpoints.ME).reply(() => [200, me]);
        }

        function TestComponent() {
          const success = usePermission(...permissions);

          return <>{`${success}`}</>;
        }
        subject = render(
          <Provider store={store}>
            <TestComponent />
          </Provider>,
        );

        await act(async () => {
          await nextUpdate();
        });
      }
    });

    describe('useArchivedPermission', () => {
      describe('with event in route', () => {
        it('returns true if the event is not archived', async () => {
          await renderComponent(
            { username: 'staff', staff: true, superuser: false, permissions: ['tracker.view_event'] },
            false,
            'tracker.view_event',
          );
          expect(subject.getByText('true')).not.toBeNull();
        });

        it('returns false if the event is archived', async () => {
          await renderComponent(
            {
              username: 'staff',
              staff: true,
              superuser: false,
              permissions: ['tracker.view_event'],
            },
            true,
            'tracker.view_event',
          );
          expect(subject.getByText('false')).not.toBeNull();
        });

        it('returns false if the event cannot be retrieved', async () => {
          await renderComponent(
            {
              username: 'staff',
              staff: true,
              superuser: false,
              permissions: ['tracker.view_event'],
            },
            null,
            'tracker.view_event',
          );
          expect(subject.getByText('false')).not.toBeNull();
        });

        async function renderComponent(me: Me, archived: boolean | null, ...permissions: Permission[]) {
          mock.onGet('//testserver/' + Endpoints.ME).reply(() => [200, me]);
          if (archived != null) {
            mock
              .onGet('//testserver/' + Endpoints.EVENTS)
              .reply(() => [200, getFixturePagedEvent({ id: 1, archived })]);
          }

          function TestComponent() {
            const success = useArchivedPermission(...permissions);

            return <>{`${success}`}</>;
          }

          subject = render(
            <Provider store={store}>
              <StaticRouter location={`/1`}>
                <Routes>
                  <Route path="/:eventId" element={<TestComponent />} />
                </Routes>
              </StaticRouter>
            </Provider>,
          );

          await act(async () => {
            await nextUpdate();
          });
        }
      });

      describe('with event provided to hook', () => {
        it('returns true if the event is not archived', async () => {
          await renderComponent(
            { username: 'staff', staff: true, superuser: false, permissions: ['tracker.view_event'] },
            processEvent(getFixtureEvent({ archived: false })),
            'tracker.view_event',
          );
          expect(subject.getByText('true')).not.toBeNull();
        });

        it('returns false if the event is archived', async () => {
          await renderComponent(
            {
              username: 'staff',
              staff: true,
              superuser: false,
              permissions: ['tracker.view_event'],
            },
            processEvent(getFixtureEvent({ archived: true })),
            'tracker.view_event',
          );
          expect(subject.getByText('false')).not.toBeNull();
        });

        async function renderComponent(me: Me, event: Event, ...permissions: Permission[]) {
          mock.onGet('//testserver/' + Endpoints.ME).reply(() => [200, me]);

          function TestComponent() {
            const success = useArchivedPermission(event, ...permissions);

            return <>{`${success}`}</>;
          }

          subject = render(
            <Provider store={store}>
              <TestComponent />
            </Provider>,
          );

          await act(async () => {
            await nextUpdate();
          });
        }
      });
    });
  });

  describe('useDonation', () => {
    it('will not fetch if the donation is already included', async () => {
      await renderComponent(true);
      expect(mock.history.get.length).toBe(1);

      expect(subject.getByText('1')).not.toBeNull();
    });

    it('will fetch if the donation is not included', async () => {
      await renderComponent(true, 500);
      expect(mock.history.get.length).toBe(2);

      // wait for the lazy fetch to come back
      await act(async () => await nextUpdate());

      expect(subject.getByText('500')).not.toBeNull();
    });

    it('displays error if donation does not exist at all', async () => {
      await renderComponent(false, 500);
      expect(mock.history.get.length).toBe(2);

      // wait for the lazy fetch to come back
      await act(async () => await nextUpdate());

      expect(subject.getByText('Not found')).not.toBeNull();
    });

    async function renderComponent(include: boolean, id?: number) {
      const donations = getFixturePagedDonations();
      id = id ?? donations.results[0].id;
      mock.onGet('//testserver/' + Endpoints.DONATIONS()).reply(config => {
        return [
          200,
          config.params.id == null
            ? donations
            : {
                count: include ? 1 : 0,
                previous: null,
                next: null,
                results: include ? [{ ...donations.results[0], id }] : [],
              },
        ];
      });

      function TestComponent() {
        const { data, error } = useDonation(id!);

        return <>{data ? data.id : <APIErrorList errors={error} />}</>;
      }

      function TestParent() {
        // ensures prefetch
        const { data } = useDonationsQuery();
        return data == null ? <>loading</> : <TestComponent />;
      }

      subject = render(
        <Provider store={store}>
          <TestParent />
        </Provider>,
      );

      await act(async () => {
        await nextUpdate();
      });
    }
  });

  async function nextUpdate() {
    return await new Promise<RootState>(resolve => {
      const unsub = store.subscribe(() => {
        unsub();
        resolve(store.getState());
      });
    });
  }
});
