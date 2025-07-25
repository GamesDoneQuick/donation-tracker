import React from 'react';
import { Outlet, Route, Routes } from 'react-router';
import { BrowserRouter, Link } from 'react-router-dom';

import { useConstants } from '@common/Constants';
import Loading from '@common/Loading';
import { useEventsQuery, usePermission, useTrackerInit } from '@public/apiv2/hooks';
import Dropdown from '@public/dropdown';
import Spinner from '@public/spinner';

import NotFound from '../public/notFound';
import ScheduleEditor from './scheduleEditor';
import TotalWatch from './totalWatch';

const ProcessPendingBids = React.lazy(
  () => import('./donationProcessing/processPendingBids' /* webpackChunkName: 'donationProcessing' */),
);

const EventMenuComponents = {};

function EventMenu(name) {
  return (
    EventMenuComponents[name] ||
    (EventMenuComponents[name] = function EventMenuInner() {
      const { data: events, isLoading } = useEventsQuery();
      const sortedEvents = React.useMemo(
        () => (events ?? []).toSorted((a, b) => b.datetime.toSeconds() - a.datetime.toSeconds()),
        [events],
      );

      return (
        <Spinner spinning={isLoading}>
          {name}
          <ul style={{ display: 'block' }}>
            {name === 'Process Pending Bids' && (
              <li>
                <Link to="@all">All Events</Link>
              </li>
            )}
            {sortedEvents &&
              sortedEvents.map(e => (
                <li key={e.id}>
                  <Link to={`${e.id}`}>{e.short}</Link>
                  {e.archived && '🔒'}
                </li>
              ))}
          </ul>
        </Spinner>
      );
    })
  );
}

function DropdownMenu({ name, path }) {
  const { data: events } = useEventsQuery();
  const sortedEvents = React.useMemo(
    () => (events ?? []).toSorted((a, b) => b.datetime.toSeconds() - a.datetime.toSeconds()),
    [events],
  );

  return (
    <Dropdown closeOnClick={true} label={name}>
      <div
        style={{
          border: '1px solid',
          position: 'absolute',
          backgroundColor: 'white',
          minWidth: '200px',
          maxHeight: '120px',
          overflowY: 'auto',
        }}>
        <ul style={{ display: 'block' }}>
          {name === 'Process Pending Bids' && (
            <li>
              <Link to={`${path}/@all`}>All Events</Link>
            </li>
          )}
          {sortedEvents &&
            sortedEvents.map(e => (
              <li key={e.id}>
                <Link to={`${path}/${e.id}`}>{e.short}</Link>
                {e.archived && '🔒'}
              </li>
            ))}
        </ul>
      </div>
    </Dropdown>
  );
}

function Menu() {
  const { ADMIN_ROOT } = useConstants();
  const canViewBids = usePermission('tracker.view_bid');
  const { data, isFetching } = useEventsQuery();

  return (
    <div style={{ height: 60, display: 'flex', alignItems: 'center' }}>
      <Spinner spinning={isFetching} showPartial={!!data}>
        {ADMIN_ROOT && (
          <>
            <a href={ADMIN_ROOT}>Admin Home</a>
            &mdash;
          </>
        )}
        <DropdownMenu name="Schedule Editor" path="schedule_editor" />
        {canViewBids && (
          <>
            &mdash;
            <DropdownMenu name="Process Pending Bids" path="process_pending_bids" />
          </>
        )}
      </Spinner>
    </div>
  );
}

function App({ rootPath }) {
  useTrackerInit();
  const { isLoading } = useEventsQuery();
  const canViewBids = usePermission('tracker.view_bid');
  const { ROOT_PATH } = useConstants();

  return (
    <Spinner spinning={isLoading}>
      <BrowserRouter basename={ROOT_PATH}>
        <Routes>
          <Route path={rootPath}>
            <Route
              element={
                <>
                  <Menu />
                  <Outlet />
                </>
              }>
              <Route path="" element={<div />} />
              <Route path="schedule_editor/" element={React.createElement(EventMenu('Schedule Editor'))} />
              <Route
                path="schedule_editor/:eventId"
                element={
                  <React.Suspense fallback={<Loading />}>
                    <ScheduleEditor />
                  </React.Suspense>
                }
              />
              <Route path="total_watch/" element={React.createElement(EventMenu('Total Watch'))} />
              <Route path="total_watch/:eventId" element={<TotalWatch />} />
              {canViewBids && (
                <Route path="process_pending_bids/" element={React.createElement(EventMenu('Process Pending Bids'))} />
              )}
              {canViewBids && (
                <Route
                  path="process_pending_bids/:eventId"
                  element={
                    <React.Suspense fallback={<Loading />}>
                      <ProcessPendingBids />
                    </React.Suspense>
                  }
                />
              )}
              <Route path="*" element={<NotFound />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </Spinner>
  );
}

export default App;
