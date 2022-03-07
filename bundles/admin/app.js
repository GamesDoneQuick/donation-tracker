import React from 'react';
import Loadable from 'react-loadable';
import { useDispatch, useSelector } from 'react-redux';
import { Route, Switch, useRouteMatch } from 'react-router';
import { Link } from 'react-router-dom';

import { useConstants } from '@common/Constants';
import Loading from '@common/Loading';
import { actions } from '@public/api';
import { usePermission } from '@public/api/helpers/auth';
import Dropdown from '@public/dropdown';
import Spinner from '@public/spinner';

import { setAPIRoot } from '@tracker/Endpoints';

import ScheduleEditor from './scheduleEditor';

const Interstitials = Loadable({
  loader: () => import('./interstitials' /* webpackChunkName: 'interstitials' */),
  loading: Loading,
});

const ReadDonations = Loadable({
  loader: () => import('./donationProcessing/readDonations' /* webpackChunkName: 'donationProcessing' */),
  loading: Loading,
});

const ProcessDonations = Loadable({
  loader: () => import('./donationProcessing/processDonations' /* webpackChunkName: 'donationProcessing' */),
  loading: Loading,
});

const ProcessPendingBids = Loadable({
  loader: () => import('./donationProcessing/processPendingBids' /* webpackChunkName: 'donationProcessing' */),
  loading: Loading,
});

const EventMenuComponents = {};

function EventMenu(name, path) {
  return (
    EventMenuComponents[name] ||
    (EventMenuComponents[name] = function EventMenuInner() {
      const { events, status } = useSelector(state => ({
        events: state.models.event,
        status: state.status,
      }));
      const url = useRouteMatch().url;
      path = path || url;
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
                  <Link to={`${path}/${e.pk}`}>{e.short}</Link>
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
  const match = useRouteMatch();

  const events = useSelector(state => state.models.event);
  const sortedEvents = React.useMemo(() => [...(events || [])].sort((a, b) => b.datetime.localeCompare(a.datetime)), [
    events,
  ]);

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
                <Link to={`${match.url}/${path}/${e.pk}`}>{e.short}</Link>
                {(!e.allow_donations || e.locked) && '🔒'}
              </li>
            ))}
        </ul>
      </div>
    </Dropdown>
  );
}

const App = () => {
  const match = useRouteMatch();
  const dispatch = useDispatch();

  const [ready, setReady] = React.useState(false);

  const { status } = useSelector(state => ({
    status: state.status,
  }));

  const { API_ROOT, ADMIN_ROOT } = useConstants();
  const canChangeDonations = usePermission('tracker.change_donation');
  const canChangeBids = usePermission('tracker.change_bid');

  React.useEffect(() => {
    setAPIRoot(API_ROOT);
    setReady(true);
  }, [API_ROOT]);

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
    <div style={{ position: 'relative', display: 'flex', height: 'calc(100vh - 51px)', flexDirection: 'column' }}>
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
          {canChangeDonations && (
            <>
              &mdash;
              <DropdownMenu name="Process Donations" path="process_donations" />
              &mdash;
              <DropdownMenu name="Read Donations" path="read_donations" />
            </>
          )}
          {canChangeBids && (
            <>
              &mdash;
              <DropdownMenu name="Process Pending Bids" path="process_pending_bids" />
            </>
          )}
        </Spinner>
      </div>
      <Spinner spinning={!ready}>
        <div style={{ flex: '1 0 1', overflow: 'auto' }}>
          <Switch>
            <Route path={`${match.url}/schedule_editor/`} exact component={EventMenu('Schedule Editor')} />
            <Route path={`${match.url}/schedule_editor/:event`} component={ScheduleEditor} />
            <Route path={`${match.url}/interstitials/:event`} component={Interstitials} />
            {canChangeDonations && (
              <Route path={`${match.url}/read_donations/`} exact component={EventMenu('Read Donations')} />
            )}
            {canChangeDonations && <Route path={`${match.url}/read_donations/:event`} component={ReadDonations} />}
            {canChangeDonations && (
              <Route path={`${match.url}/process_donations/`} exact component={EventMenu('Process Donations')} />
            )}
            {canChangeDonations && (
              <Route path={`${match.url}/process_donations/:event`} component={ProcessDonations} />
            )}
            {canChangeBids && (
              <Route path={`${match.url}/process_pending_bids/`} exact component={EventMenu('Process Pending Bids')} />
            )}
            {canChangeBids && (
              <Route path={`${match.url}/process_pending_bids/:event`} component={ProcessPendingBids} />
            )}
          </Switch>
        </div>
      </Spinner>
    </div>
  );
};

export default App;
