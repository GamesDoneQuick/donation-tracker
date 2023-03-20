import * as React from 'react';
import { Route, Switch } from 'react-router';

import { usePermission } from '@public/api/helpers/auth';
import { ProcessingSocket } from '@public/apiv2/sockets/ProcessingSocket';

import ProcessDonations from './ProcessDonations';
import useProcessingStore from './ProcessingStore';
import ThemeProvider from './Theming';

import './Theming.mod.css';

export default function ProcessingV2({ rootPath }: { rootPath: string }) {
  const canChangeDonations = usePermission('tracker.change_donation');
  const { processDonation } = useProcessingStore();

  React.useEffect(() => {
    const unsubscribe = ProcessingSocket.on('*', event => {
      processDonation(event.donation, event.action);
    });
    return unsubscribe;
  }, [processDonation]);

  return (
    <ThemeProvider>
      <Switch>
        {canChangeDonations && (
          <Route path={`${rootPath}/v2/:eventId/processing/donations`} exact component={ProcessDonations} />
        )}
      </Switch>
    </ThemeProvider>
  );
}
