import * as React from 'react';
import { Router, Route, RouteComponentProps, Switch } from 'react-router-dom';

import DonateInitializer from './donation/components/DonateInitializer';
import EventRouter from './events/components/EventRouter';
import NotFound from './router/components/NotFound';
import { Routes, createTrackerHistory } from './router/RouterUtils';
import { useConstants } from '../common/Constants';
import { setAPIRoot } from './Endpoints';

const App = (props: React.ComponentProps<typeof DonateInitializer>) => {
  const history = React.useMemo(() => createTrackerHistory(props.ROOT_PATH), [props.ROOT_PATH]);
  const { API_ROOT } = useConstants();
  const [ready, setReady] = React.useState(false);

  React.useEffect(() => {
    setAPIRoot(API_ROOT);
    setReady(true);
  }, [API_ROOT]);

  return (
    <>
      {ready && (
        <Router history={history}>
          <Switch>
            {/* TODO: Remove `EVENT_DONATE` from here once it gets normalized */}
            <Route path={[Routes.EVENT_BASE(':eventId'), Routes.EVENT_DONATE(':eventId')]}>
              {({ match }: RouteComponentProps<{ eventId: string }>) => {
                // This has to be done as a custom child to pass through DonateInitializerProps
                const { eventId } = match.params;
                return <EventRouter {...props} eventId={eventId} />;
              }}
            </Route>
            <NotFound />
          </Switch>
        </Router>
      )}
    </>
  );
};

export default App;
