import * as React from 'react';
import { Route, RouteComponentProps, Switch } from 'react-router-dom';

import Donate from '../../donation/components/Donate';
import DonateInitializer from '../../donation/components/DonateInitializer';
import Prize from '../../prizes/components/Prize';
import Prizes from '../../prizes/components/Prizes';
import { Routes } from '../../router/RouterUtils';
import NotFound from '../../router/components/NotFound';

const EventRouter = (props: any) => {
  // TODO: type this better when DonateInitializer doesn't need page-load props
  const { eventId } = props;

  return (
    <Switch>
      {window.SWEEPSTAKES_URL && (
        <Route exact path={Routes.EVENT_PRIZES(eventId)}>
          <Prizes eventId={eventId} />
        </Route>
      )}
      {window.SWEEPSTAKES_URL && (
        <Route exact path={Routes.EVENT_PRIZE(eventId, ':prizeId')}>
          {({ match }: RouteComponentProps<{ eventId: string; prizeId: string }>) => (
            <Prize prizeId={match.params.prizeId} />
          )}
        </Route>
      )}
      <Route exact path={Routes.EVENT_DONATE(eventId)}>
        {({ match }: RouteComponentProps<{ eventId: string }>) => (
          <React.Fragment>
            <DonateInitializer {...props} />
            <Donate eventId={eventId} />
          </React.Fragment>
        )}
      </Route>
      <NotFound />
    </Switch>
  );
};

export default EventRouter;
