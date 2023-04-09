import * as React from 'react';
import { Route, RouteChildrenProps, RouteComponentProps, Router, Switch } from 'react-router-dom';

import { useConstants } from '@common/Constants';

import { AnalyticsEvent, setAnalyticsURL, track } from './analytics/Analytics';
import DonateInitializer from './donation/components/DonateInitializer';
import EventRouter from './events/components/EventRouter';
import NotFound from './router/components/NotFound';
import { createTrackerHistory, Routes } from './router/RouterUtils';
import { setAPIRoot } from './Endpoints';

const App = (props: React.ComponentProps<typeof DonateInitializer>) => {
  const history = React.useMemo(() => createTrackerHistory(props.ROOT_PATH), [props.ROOT_PATH]);
  const { ANALYTICS_URL, API_ROOT } = useConstants();
  const [ready, setReady] = React.useState(false);

  React.useEffect(() => {
    setAPIRoot(API_ROOT);
    setAnalyticsURL(ANALYTICS_URL);
    setReady(true);
  }, [API_ROOT, ANALYTICS_URL]);

  React.useLayoutEffect(() => {
    track(AnalyticsEvent.TRACKER_APP_LOADED, {
      react_render_finished_ms: Math.floor(window.performance.now()),
    });
  }, []);

  return (
    <>
      {ready && (
        <Router history={history}>
          <Switch>
            {/* TODO: Remove `EVENT_DONATE` from here once it gets normalized */}
            <Route path={[Routes.EVENT_BASE(':eventId'), Routes.EVENT_DONATE(':eventId')]} component={EventRouter} />
            <NotFound />
          </Switch>
        </Router>
      )}
    </>
  );
};

export default App;
