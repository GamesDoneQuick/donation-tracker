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
  const { loadDonations, processDonation } = useProcessingStore();

  React.useEffect(() => {
    const unsubActions = ProcessingSocket.on('processing_action', event => {
      if (event.action === 'unprocessed') {
        loadDonations([event.donation]);
      } else {
        processDonation(event.donation, event.action, false);
      }
    });

    const unsubNewDonations = ProcessingSocket.on('donation_received', event => {
      loadDonations([event.donation]);
    });
    return () => {
      unsubActions();
      unsubNewDonations();
    };
  }, [loadDonations, processDonation]);

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
