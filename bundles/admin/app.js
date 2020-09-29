import React from 'react';
import { Route, useRouteMatch } from 'react-router';
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

const App = () => {
  const match = useRouteMatch();
  const dispatch = useDispatch();
  const [ready, setReady] = React.useState(false);

  const { events, status } = useSelector(state => ({
    events: state.models.event,
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
    ready && (
      <div style={{ position: 'relative', display: 'flex', height: 'calc(100vh - 51px)', flexDirection: 'column' }}>
        <div style={{ height: 60, display: 'flex', alignItems: 'center' }}>
          <Spinner spinning={status.event === 'loading'}>
            Schedule Editor
            <Dropdown closeOnClick={true}>
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
                    events.map(e => {
                      return (
                        <li key={e.pk}>
                          <Link to={`${match.url}/schedule_editor/${e.pk}`}>{e.short}</Link>
                        </li>
                      );
                    })}
                </ul>
              </div>
            </Dropdown>
            &mdash; Interstitials
            <Dropdown closeOnClick={true}>
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
                    events.map(e => {
                      return (
                        <li key={e.pk}>
                          <Link to={`${match.url}/interstitials/${e.pk}`}>{e.short}</Link>
                        </li>
                      );
                    })}
                </ul>
              </div>
            </Dropdown>
          </Spinner>
        </div>
        <div style={{ flex: '1 0 1', overflow: 'auto' }}>
          <Route path={`${match.url}/schedule_editor/:event`} component={ScheduleEditor} />
          <Route path={`${match.url}/interstitials/:event`} component={Interstitials} />
        </div>
      </div>
    )
  );
};

export default App;
