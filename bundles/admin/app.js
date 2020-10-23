import React from 'react';
import { Route, Switch, useRouteMatch } from 'react-router';
import { Link } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import Loadable from 'react-loadable';

import Spinner from '../public/spinner';
import Dropdown from '../public/dropdown';
import { actions } from '../public/api';
import ScheduleEditor from './scheduleEditor';
import Loading from '../common/Loading';
import { useConstants } from '../common/Constants';
import { setAPIRoot } from '../tracker/Endpoints';

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

      return (
        <Spinner spinning={status.event === 'loading'}>
          {name}
          <ul style={{ display: 'block' }}>
            {events &&
              events.map(e => (
                <li key={e.pk}>
                  <Link to={`${path}/${e.pk}`}>{e.short}</Link>
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
          {events &&
            events.map(e => (
              <li key={e.pk}>
                <Link to={`${match.url}/${path}/${e.pk}`}>{e.short}</Link>
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

  const { API_ROOT } = useConstants();

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
          <DropdownMenu name="Schedule Editor" path="schedule_editor" />
          &mdash;
          <DropdownMenu name="Interstitials" path="interstitials" />
          &mdash;
          <DropdownMenu name="Process Donations" path="process_donations" />
          &mdash;
          <DropdownMenu name="Read Donations" path="read_donations" />
        </Spinner>
      </div>
      <div style={{ flex: '1 0 1', overflow: 'auto' }}>
        <Switch>
          <Route path={`${match.url}/schedule_editor/:event`} component={ScheduleEditor} />
          <Route path={`${match.url}/interstitials/:event`} component={Interstitials} />
          <Route path={`${match.url}/read_donations/`} exact component={EventMenu('Read Donations')} />
          <Route path={`${match.url}/read_donations/:event`} component={ReadDonations} />
          <Route path={`${match.url}/process_donations/`} exact component={EventMenu('Process Donations')} />
          <Route path={`${match.url}/process_donations/:event`} component={ProcessDonations} />
        </Switch>
      </div>
    </div>
  );
};

export default App;
