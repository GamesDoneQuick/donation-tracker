import * as React from 'react';
import { Route, Switch, useRouteMatch } from 'react-router-dom';

import { useConstants } from '@common/Constants';

import Donate from '@tracker/donation/components/Donate';
import Prize from '@tracker/prizes/components/Prize';
import Prizes from '@tracker/prizes/components/Prizes';
import NotFound from '@tracker/router/components/NotFound';
import { Routes } from '@tracker/router/RouterUtils';

function PrizePage() {
  const routeMatch = useRouteMatch<{ prizeId: string }>();
  const { prizeId } = routeMatch.params;

  return <Prize prizeId={prizeId} />;
}

const EventRouter = () => {
  const routeMatch = useRouteMatch<{ eventId: string }>();
  // TODO: type this better when DonateInitializer doesn't need page-load props
  const eventId = routeMatch.params.eventId;
  const { SWEEPSTAKES_URL } = useConstants();

  return (
    <Switch>
      {SWEEPSTAKES_URL && (
        <Route exact path={Routes.EVENT_PRIZES(eventId)}>
          <Prizes eventId={eventId} />
        </Route>
      )}
      {SWEEPSTAKES_URL && <Route exact path={Routes.EVENT_PRIZE(eventId, ':prizeId')} component={PrizePage} />}
      <Route exact path={Routes.EVENT_DONATE(eventId)}>
        <Donate eventId={eventId} />
      </Route>
      <NotFound />
    </Switch>
  );
};

export default EventRouter;
