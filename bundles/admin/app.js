import React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Outlet, Route, Routes } from 'react-router';
import { BrowserRouter, Link } from 'react-router-dom';

import { useConstants } from '@common/Constants';
import Loading from '@common/Loading';
import { actions } from '@public/api';
import { usePermission } from '@public/api/helpers/auth';
import V2HTTPUtils from '@public/apiv2/HTTPUtils';
import Dropdown from '@public/dropdown';
import Spinner from '@public/spinner';

import { setAPIRoot } from '@tracker/Endpoints';

import NotFound from '../public/notFound';
import ScheduleEditor from './scheduleEditor';
import TotalWatch from './totalWatch';

const Interstitials = React.lazy(() => import('./interstitials' /* webpackChunkName: 'interstitials' */));

const ProcessPendingBids = React.lazy(() =>
  import('./donationProcessing/processPendingBids' /* webpackChunkName: 'donationProcessing' */),
);

const EventMenuComponents = {};

function EventMenu(name) {
  return (
    EventMenuComponents[name] ||
    (EventMenuComponents[name] = function EventMenuInner() {
      const { events, status } = useSelector(state => ({
        events: state.models.event,
        status: state.status,
      }));
      const sortedEvents = React.useMemo(
        () => [...(events || [])].sort((a, b) => b.datetime.localeCompare(a.datetime)),
        [events],
      );

      return (
        <Spinner spinning={status.event === 'loading'}>
          {name}
          <ul style={{ display: 'block' }}>
            {sortedEvents &&
              sortedEvents.map(e => (
                <li key={e.pk}>
                  <Link to={`${e.pk}`}>{e.short}</Link>
                  {(!e.allow_donations || e.locked) && '🔒'}
                </li>
              ))}
          </ul>
        </Spinner>
      );
    })
  );
}

function DropdownMenu({ name, path }) {
  const events = useSelector(state => state.models.event);
  const sortedEvents = React.useMemo(
    () => [...(events || [])].sort((a, b) => b.datetime.localeCompare(a.datetime)),
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
          {sortedEvents &&
            sortedEvents.map(e => (
              <li key={e.pk}>
                <Link to={`${path}/${e.pk}`}>{e.short}</Link>
                {(!e.allow_donations || e.locked) && '🔒'}
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
  const { status } = useSelector(state => ({
    status: state.status,
  }));
  return (
    <div style={{ height: 60, display: 'flex', alignItems: 'center' }}>
      <Spinner spinning={status.event !== 'success'}>
        {ADMIN_ROOT && (
          <>
            <a href={ADMIN_ROOT}>Admin Home</a>
            &mdash;
          </>
        )}
        <DropdownMenu name="Schedule Editor" path="schedule_editor" />
        &mdash;
        <DropdownMenu name="Interstitials" path="interstitials" />
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
  const dispatch = useDispatch();

  const [ready, setReady] = React.useState(false);

  const { status } = useSelector(state => ({
    status: state.status,
  }));

  const { API_ROOT, APIV2_ROOT } = useConstants();
  const canViewBids = usePermission('tracker.view_bid');

  React.useLayoutEffect(() => {
    setAPIRoot(API_ROOT);
    V2HTTPUtils.setAPIRoot(APIV2_ROOT);
    setReady(true);
  }, [API_ROOT, APIV2_ROOT]);

  React.useEffect(() => {
    if (ready) {
      dispatch(actions.singletons.fetchMe());
    }
  }, [dispatch, ready]);

  React.useEffect(() => {
    if (status.event !== 'success' && status.event !== 'loading' && ready) {
      dispatch(actions.models.loadModels('event'));
    }
  }, [dispatch, status.event, ready]);

  return (
    <Spinner spinning={!ready}>
      <BrowserRouter>
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
              <Route
                path="interstitials/:eventId"
                element={
                  <React.Suspense fallback={<Loading />}>
                    <Interstitials />
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
