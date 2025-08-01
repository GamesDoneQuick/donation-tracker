import React from 'react';
import MockAdapter from 'axios-mock-adapter';
import { DateTime } from 'luxon';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { Provider } from 'react-redux';
import { Route, Routes } from 'react-router';
import { StaticRouter } from 'react-router-dom/server';
import { act, cleanup, fireEvent, render } from '@testing-library/react';

import Constants, { DefaultConstants } from '@common/Constants';
import { APIAd, APIEvent, APIInterview, APIPrize, APIRun, Me, PaginationInfo } from '@public/apiv2/APITypes';
import Endpoints from '@public/apiv2/Endpoints';
import { parseTime, toInputTime } from '@public/apiv2/helpers/luxon';
import HTTPUtils from '@public/apiv2/HTTPUtils';
import { setRoot } from '@public/apiv2/reducers/apiRoot';
import { trackerApi } from '@public/apiv2/reducers/trackerApi';
import { APIError } from '@public/apiv2/reducers/trackerBaseApi';
import { store } from '@public/apiv2/Store';

import { getFixturePagedAds } from '@spec/fixtures/ad';
import { getFixtureError } from '@spec/fixtures/error';
import { getFixturePagedEvent } from '@spec/fixtures/event';
import { getFixturePagedInterviews } from '@spec/fixtures/interview';
import { getFixturePagedPrizes } from '@spec/fixtures/Prize';
import { getFixturePagedRuns } from '@spec/fixtures/run';
import { getFixtureValue } from '@spec/fixtures/util';
import { getByChainedTestId, queryByChainedTestId, waitForAPIErrors, waitForSpinner } from '@spec/helpers/rtl';

import ScheduleEditor from './index';

import styles from './styles.mod.css';

describe('ScheduleEditor', () => {
  let subject: ReturnType<typeof render>;
  const eventId = 1;
  let CONSTANTS: Partial<typeof DefaultConstants> = {};
  let mock: MockAdapter;
  let me: Me;
  let events: PaginationInfo<APIEvent>;
  let eventError: APIError;
  let eventCode = 200;
  let runs: PaginationInfo<APIRun>;
  let runError: APIError;
  let runCode = 200;
  let interviews: PaginationInfo<APIInterview>;
  let interviewError: APIError;
  let interviewCode = 200;
  let ads: PaginationInfo<APIAd>;
  let adError: APIError;
  let adCode = 200;
  let prizes: PaginationInfo<APIPrize>;
  let prizeError: APIError;
  let prizeCode = 200;

  beforeAll(() => {
    mock = new MockAdapter(HTTPUtils.getInstance());
  });

  beforeEach(() => {
    CONSTANTS = {};
    store.dispatch(setRoot({ root: '//testserver/', limit: 500, csrfToken: 'deadbeef' }));
    mock.reset();
    me = {
      username: 'test',
      staff: true,
      superuser: false,
      permissions: ['tracker.change_speedrun', 'tracker.view_speedrun'],
    };
    events = getFixturePagedEvent();
    eventError = getFixtureError();
    eventCode = 200;
    runs = getFixturePagedRuns();
    runError = getFixtureError();
    runCode = 200;
    interviews = getFixturePagedInterviews();
    interviewError = getFixtureError();
    interviewCode = 200;
    ads = getFixturePagedAds();
    adError = getFixtureError();
    adCode = 200;
    prizes = getFixturePagedPrizes([{ startrun: runs.results[2].id, endrun: runs.results[2].id }]);
    prizeError = getFixtureError();
    prizeCode = 200;
    mock.onGet('//testserver/' + Endpoints.ME).reply(() => [200, me]);
    mock.onGet('//testserver/' + Endpoints.EVENTS).reply(getFixtureValue(() => eventCode, events, eventError));
    mock.onGet('//testserver/' + Endpoints.RUNS(eventId)).reply(getFixtureValue(() => runCode, runs, runError));
    mock
      .onGet('//testserver/' + Endpoints.INTERVIEWS(eventId))
      .reply(getFixtureValue(() => interviewCode, interviews, interviewError));
    mock.onGet('//testserver/' + Endpoints.ADS(eventId)).reply(getFixtureValue(() => adCode, ads, adError));
    mock.onGet('//testserver/' + Endpoints.PRIZES(eventId)).reply(getFixtureValue(() => prizeCode, prizes, prizeError));
  });

  afterAll(() => {
    mock.restore();
  });

  it('loads events, runs, and interviews on mount', async () => {
    await renderComponent();
    expect(trackerApi.util.selectCachedArgsForQuery(store.getState(), 'runs')).toContain({
      urlParams: eventId,
      queryParams: { all: '' },
    });
    expect(trackerApi.util.selectCachedArgsForQuery(store.getState(), 'events')).toContain(undefined);
    expect(trackerApi.util.selectCachedArgsForQuery(store.getState(), 'interviews')).toContain({
      urlParams: eventId,
      queryParams: {},
    });
    expect(trackerApi.util.selectCachedArgsForQuery(store.getState(), 'ads')).toEqual([]);
    expect(subject.getByText('Show Interviews')).not.toBeNull();
    expect(subject.queryByText('Show Ads')).toBeNull();
  });

  describe('with permissions', () => {
    it('loads all interviews on mount', async () => {
      me.permissions.push('tracker.view_interview');
      await renderComponent();
      expect(trackerApi.util.selectCachedArgsForQuery(store.getState(), 'interviews')).toContain({
        urlParams: eventId,
        queryParams: { all: '' },
      });
    });

    it('loads ads on mount', async () => {
      me.permissions.push('tracker.view_ad');
      await renderComponent();
      expect(trackerApi.util.selectCachedArgsForQuery(store.getState(), 'ads')).toContain({
        urlParams: eventId,
      });
      expect(subject.getByText('Show Ads')).not.toBeNull();
    });

    it('loads all prizes on mount', async () => {
      CONSTANTS.SWEEPSTAKES_URL = 'https://example.com/';
      me.permissions.push('tracker.view_prize');
      await renderComponent();
      expect(trackerApi.util.selectCachedArgsForQuery(store.getState(), 'prizes')).toContain({
        urlParams: { eventId, feed: 'all' },
      });
    });
  });

  it('shows an error if events fail to load', async () => {
    eventCode = 500;
    await renderComponent();
    expect(subject.getByTestId('api-errors')).toBeTruthy();
  });

  it('shows an error if runs fail to load', async () => {
    runCode = 500;
    await renderComponent();
    expect(subject.getByTestId('api-errors')).toBeTruthy();
  });

  it('shows an error if interviews fail to load', async () => {
    interviewCode = 500;
    await renderComponent();
    expect(subject.getByTestId('api-errors')).toBeTruthy();
  });

  it('shows an error if ads fail to load', async () => {
    me.permissions.push('tracker.view_ad');
    adCode = 500;
    await renderComponent();
    expect(subject.getByTestId('api-errors')).toBeTruthy();
  });

  it('shows a message if runs are empty', async () => {
    runs.results = [];
    await renderComponent();
    expect(subject.queryByTestId('api-errors')).toBeNull();
    expect(subject.queryByTestId('run-last')).toBeNull();
    expect(subject.getByTestId('empty-event')).toBeTruthy();
  });

  it('shows anchor handles for anchorable runs', async () => {
    await renderComponent();
    // can't anchor the first run
    expect(queryByChainedTestId(subject, 'run-1', 'toggle-anchor')).toBeNull();
    expect(getByChainedTestId(subject, 'run-2', 'toggle-anchor')).not.toBeNull();
    expect(getByChainedTestId(subject, 'run-3', 'toggle-anchor')).not.toBeNull();

    // can't anchor unorderable runs
    expect(queryByChainedTestId(subject, 'run-4', 'toggle-anchor')).toBeNull();
    expect(queryByChainedTestId(subject, 'run-5', 'toggle-anchor')).toBeNull();
  });

  it('shows drag handles for moveable runs', async () => {
    await renderComponent();
    expect(getByChainedTestId(subject, 'run-1', 'drag-handle')).not.toBeNull();

    // can't drag anchored runs
    expect(queryByChainedTestId(subject, 'run-2', 'drag-handle')).toBeNull();

    expect(getByChainedTestId(subject, 'run-3', 'drag-handle')).not.toBeNull();
    expect(getByChainedTestId(subject, 'run-4', 'drag-handle')).not.toBeNull();

    // can't drag runs with no duration
    expect(queryByChainedTestId(subject, 'run-5', 'drag-handle')).toBeNull();
  });

  it('shows unordered buttons for ordered, unanchored runs with no prizes or interstitials', async () => {
    CONSTANTS.SWEEPSTAKES_URL = 'https://example.com/';
    interviews.results[0].order = runs.results[0].order!;
    interviews.results[0].anchor = runs.results[0].id;
    await renderComponent();

    let handle = getByChainedTestId<HTMLButtonElement>(subject, 'run-1', 'unorder-run');
    expect(handle).not.toBeNull();
    expect(handle.disabled).toBeTrue();

    // can't unorder anchored runs
    expect(queryByChainedTestId(subject, 'run-2', 'unorder-run')).toBeNull();

    handle = getByChainedTestId(subject, 'run-3', 'unorder-run');
    expect(handle).not.toBeNull();
    expect(handle.disabled).toBeTrue();

    // already unordered
    expect(queryByChainedTestId(subject, 'run-4', 'unorder-run')).toBeNull();
    expect(queryByChainedTestId(subject, 'run-5', 'unorder-run')).toBeNull();
  });

  it('shows no handles and does not try to load unordered runs if the user has no permissions', async () => {
    me.permissions = [];
    await renderComponent();
    expect(trackerApi.util.selectCachedArgsForQuery(store.getState(), 'runs')).toContain({
      urlParams: eventId,
      queryParams: {},
    });
    expect((subject.getAllByTestId('toggle-anchor')[0] as HTMLButtonElement).disabled).toBeTrue();
    expect(subject.queryByTestId('drag-handle')).toBeNull();
  });

  it('does not show anchor icon for unanchored interstitials', async () => {
    await renderComponent();
    expect(subject.getByTestId(`interview-${interviews.results[0].id}`).querySelector('.fa.fa-anchor')).toBeNull();
  });

  it('shows anchor icon for anchored interstitials', async () => {
    interviews.results[0].anchor = 1;
    await renderComponent();
    expect(subject.getByTestId(`interview-${interviews.results[0].id}`).querySelector('.fa.fa-anchor')).not.toBeNull();
  });

  describe('with prizes enabled', () => {
    beforeEach(() => {
      CONSTANTS.SWEEPSTAKES_URL = 'https://example.com/';
    });

    it('loads prizes on mount', async () => {
      await renderComponent();
      expect(trackerApi.util.selectCachedArgsForQuery(store.getState(), 'prizes')).toContain({
        urlParams: { eventId },
      });
    });

    it('displays prize counts', async () => {
      await renderComponent();
      expect(
        subject.getByTestId(`run-${prizes.results[0].startrun}`).querySelector('.fa.fa-arrow-down')?.textContent,
      ).toEqual('1');
      expect(
        subject.getByTestId(`run-${prizes.results[0].endrun}`).querySelector('.fa.fa-arrow-up')?.textContent,
      ).toEqual('1');
    });
  });

  describe('editing', () => {
    beforeEach(async () => {
      me.permissions.push('tracker.view_ad');
      await renderComponent();
    });

    it('can toggle anchor time', async () => {
      act(() => {
        fireEvent.click(getByChainedTestId(subject, 'run-2', 'toggle-anchor'));
      });

      let patch = mock.history.patch.at(0);
      expect(patch).toBeDefined();
      expect(patch?.url).toEqual(Endpoints.RUN(2));
      expect(patch?.data).toEqual(JSON.stringify({ anchor_time: null }));

      await waitForAPIErrors(subject);

      mock.resetHistory();

      act(() => {
        fireEvent.click(getByChainedTestId(subject, 'run-3', 'toggle-anchor'));
      });

      patch = mock.history.patch.at(0);
      expect(patch).toBeDefined();
      expect(patch?.url).toEqual(Endpoints.RUN(3));
      expect(patch?.data).toEqual(JSON.stringify({ anchor_time: parseTime(runs.results[2].starttime)?.toString() }));

      await waitForAPIErrors(subject);
    });

    it('can edit anchor time', async () => {
      const adjusted = DateTime.fromISO(runs.results[1].anchor_time!).plus({ minute: 5 });
      act(() => {
        fireEvent.click(getByChainedTestId(subject, 'run-2', 'start-time', 'edit'));
      });
      act(() => {
        fireEvent.change(subject.getByTestId('run-2').querySelector('input')!, {
          target: { value: toInputTime(adjusted) },
        });
        fireEvent.click(getByChainedTestId(subject, 'run-2', 'start-time', 'accept'));
      });

      const result = mock.history.patch.at(0);
      expect(result).toBeDefined();
      expect(result?.url).toEqual(Endpoints.RUN(2));
      expect(result?.data).toEqual(JSON.stringify({ anchor_time: adjusted.toISO() }));

      await waitForAPIErrors(subject);
    });

    it('can edit run time', async () => {
      act(() => {
        fireEvent.click(getByChainedTestId(subject, 'run-1', 'run-time', 'edit'));
      });
      act(() => {
        fireEvent.change(subject.getByTestId('run-1').querySelector('input')!, { target: { value: '2:00:00' } });
        fireEvent.click(getByChainedTestId(subject, 'run-1', 'run-time', 'accept'));
      });

      const result = mock.history.patch.at(0);
      expect(result).toBeDefined();
      expect(result?.url).toEqual(Endpoints.RUN(1));
      expect(result?.data).toEqual(JSON.stringify({ run_time: '2:00:00' }));

      await waitForAPIErrors(subject);
    });

    it('can edit setup time', async () => {
      act(() => {
        fireEvent.click(getByChainedTestId(subject, 'run-1', 'setup-time', 'edit'));
      });
      act(() => {
        fireEvent.change(subject.getByTestId('run-1').querySelector('input')!, { target: { value: '0:20:00' } });
        fireEvent.click(getByChainedTestId(subject, 'run-1', 'setup-time', 'accept'));
      });

      const result = mock.history.patch.at(0);
      expect(result).toBeDefined();
      expect(result?.url).toEqual(Endpoints.RUN(1));
      expect(result?.data).toEqual(JSON.stringify({ setup_time: '0:20:00' }));

      await waitForAPIErrors(subject);
    });

    it('can remove runs from order', async () => {
      const count = mock.history.get.filter(c => /interviews|ads/.test(c.url || '')).length;
      act(() => {
        fireEvent.click(getByChainedTestId(subject, 'run-1', 'unorder-run'));
      });

      const result = mock.history.patch.at(0);
      expect(result).toBeDefined();
      expect(result?.url).toEqual(Endpoints.MOVE_RUN(1));
      expect(result?.data).toEqual(JSON.stringify({ order: null }));

      await waitForAPIErrors(subject);

      expect(mock.history.get.filter(c => /interviews|ads/.test(c.url || '')).length).toEqual(count + 2);
    });
  });

  describe('dragging', () => {
    let handle: HTMLElement;
    beforeEach(async () => {
      me.permissions.push('tracker.view_ad');
      await renderComponent();
      handle = getByChainedTestId(subject, 'run-4', 'drag-handle');
      act(() => {
        fireEvent.dragStart(handle);
      });
    });

    it('shows valid drag targets', () => {
      expect(subject.getByTestId('run-1')).toHaveClass(styles.isItemDragging);
      expect(subject.getByTestId('run-1')).toHaveClass(styles.canDrop);
      expect(subject.getByTestId('run-2')).toHaveClass(styles.isItemDragging);
      expect(subject.getByTestId('run-2')).not.toHaveClass(styles.canDrop);
      expect(subject.getByTestId('run-3')).toHaveClass(styles.isItemDragging);
      expect(subject.getByTestId('run-3')).toHaveClass(styles.canDrop);
      expect(subject.getByTestId('run-4')).not.toHaveClass(styles.isItemDragging);
      expect(subject.getByTestId('run-4')).not.toHaveClass(styles.canDrop);
      expect(subject.getByTestId('run-5')).not.toHaveClass(styles.isItemDragging);
      expect(subject.getByTestId('run-5')).not.toHaveClass(styles.canDrop);
      expect(subject.getByTestId('run-last')).toHaveClass(styles.isItemDragging);
      expect(subject.getByTestId('run-last')).toHaveClass(styles.canDrop);
    });

    describe('when hovering over a target', () => {
      beforeEach(() => {
        act(() => {
          fireEvent.dragEnter(subject.getByTestId('run-1'));
        });
      });

      it('shows the over class', () => {
        expect(subject.getByTestId('run-1')).toHaveClass(styles.isOver);
      });

      describe('when dropping on a valid target', () => {
        let count: number;
        beforeEach(() => {
          count = mock.history.get.filter(c => /interviews|ads/.test(c.url || '')).length;
          act(() => {
            fireEvent.drop(subject.getByTestId('run-1'));
            fireEvent.dragLeave(subject.getByTestId('run-1'));
            fireEvent.dragEnd(handle);
          });
        });

        it('triggers a mutation, shows the result, and refetches interviews and ads', async () => {
          const result = mock.history.patch.at(0);
          expect(result).toBeDefined();
          expect(result?.url).toEqual(Endpoints.MOVE_RUN(4));
          expect(result?.data).toEqual(JSON.stringify({ before: 1 }));

          await waitForAPIErrors(subject);

          expect(mock.history.get.filter(c => /interviews|ads/.test(c.url || '')).length).toEqual(count + 2);
        });
      });

      describe('when dropping on the last target', () => {
        beforeEach(() => {
          act(() => {
            fireEvent.dragLeave(subject.getByTestId('run-1'));
            fireEvent.dragEnter(subject.getByTestId('run-last'));
            fireEvent.drop(subject.getByTestId('run-last'));
            fireEvent.dragLeave(subject.getByTestId('run-last'));
            fireEvent.dragEnd(handle);
          });
        });

        it('triggers a mutation', async () => {
          const patch = mock.history.patch.at(0);
          expect(patch).toBeDefined();
          expect(patch?.url).toEqual(Endpoints.MOVE_RUN(4));
          expect(patch?.data).toEqual(JSON.stringify({ order: 'last' }));

          await waitForAPIErrors(subject);
        });
      });

      describe('when dropping on an invalid target', () => {
        beforeEach(() => {
          act(() => {
            fireEvent.dragLeave(subject.getByTestId('run-1'));
            fireEvent.dragEnter(subject.getByTestId('run-2'));
            fireEvent.drop(subject.getByTestId('run-2'));
            fireEvent.dragLeave(subject.getByTestId('run-2'));
            fireEvent.dragEnd(subject.getByTestId('run-2'));
          });
        });

        it('does not trigger a mutation', () => {
          expect(mock.history.patch.length).toEqual(0);
        });
      });
    });
  });

  async function renderComponent() {
    act(() => {
      store.dispatch(trackerApi.util.resetApiState());
    });
    cleanup();

    subject = render(
      <DndProvider backend={HTML5Backend}>
        <Provider store={store}>
          <Constants.Provider value={{ ...DefaultConstants, ...CONSTANTS }}>
            <StaticRouter location={`/${eventId}`}>
              <Routes>
                <Route path="/:eventId" element={<ScheduleEditor />} />
              </Routes>
            </StaticRouter>
          </Constants.Provider>
        </Provider>
      </DndProvider>,
    );

    await waitForSpinner(subject);
  }
});
