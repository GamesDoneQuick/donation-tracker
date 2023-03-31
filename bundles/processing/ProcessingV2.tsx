import * as React from 'react';
import { Route, Switch } from 'react-router';
import { Accent, AppContainer, Theme } from '@spyrothon/sparx';

import { usePermission } from '@public/api/helpers/auth';
import { ProcessingSocket } from '@public/apiv2/sockets/ProcessingSocket';

import { loadDonations } from './DonationsStore';
import ProcessDonations from './ProcessDonations';
import useProcessingStore from './ProcessingStore';
import ReadDonations from './ReadDonations';
import { useThemeStore } from './Theming';

import '../.design_system/generated/DesignSystem.css';
import '@spyrothon/sparx/style.css';

export default function ProcessingV2() {
  const canChangeDonations = usePermission('tracker.change_donation');
  const { processDonation } = useProcessingStore();
  const { theme, accent } = useThemeStore();

  React.useEffect(() => {
    const unsubActions = ProcessingSocket.on('processing_action', event => {
      loadDonations([event.donation]);
      if (event.action !== 'unprocessed') {
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
  }, [processDonation]);

  return (
    <AppContainer theme={theme as Theme} accent={accent as Accent}>
      <Switch>
        {canChangeDonations && (
          <>
            <Route path="/v2/:eventId/processing/donations" exact component={ProcessDonations} />
            <Route path="/v2/:eventId/processing/read" exact component={ReadDonations} />
          </>
        )}
      </Switch>
    </AppContainer>
  );
}
