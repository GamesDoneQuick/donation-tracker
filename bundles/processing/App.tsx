import * as React from 'react';
import { Route, Switch } from 'react-router';
import { Accent, AppContainer, Theme } from '@spyrothon/sparx';

import { useConstants } from '@common/Constants';
import { usePermission } from '@public/api/helpers/auth';
import APIClient from '@public/apiv2/APIClient';
import { setAPIRoot } from '@public/apiv2/HTTPUtils';

import { loadDonations } from './modules/donations/DonationsStore';
import useProcessingStore from './modules/processing/ProcessingStore';
import * as Theming from './modules/theming/Theming';
import ProcessDonations from './pages/ProcessDonations';
import ReadDonations from './pages/ReadDonations';

import '../.design_system/generated/DesignSystem.css';
import '@spyrothon/sparx/style.css';

export default function App() {
  const canChangeDonations = usePermission('tracker.change_donation');
  const { processDonation } = useProcessingStore();
  const { theme, accent } = Theming.useThemeStore();

  const { APIV2_ROOT } = useConstants();

  React.useEffect(() => {
    setAPIRoot(APIV2_ROOT);
  }, [APIV2_ROOT]);

  React.useEffect(() => {
    const unsubActions = APIClient.sockets.processingSocket.on('processing_action', event => {
      loadDonations([event.donation]);
      if (event.action !== 'unprocessed') {
        processDonation(event.donation, event.action, false);
      }
    });

    const unsubNewDonations = APIClient.sockets.processingSocket.on('donation_received', event => {
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
