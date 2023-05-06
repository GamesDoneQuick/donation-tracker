import * as React from 'react';
import { useQuery } from 'react-query';
import { Route, Switch } from 'react-router';
import { Accent, AppContainer, Theme } from '@spyrothon/sparx';

import { useConstants } from '@common/Constants';
import { usePermission } from '@public/api/helpers/auth';
import APIClient from '@public/apiv2/APIClient';
import { setAPIRoot } from '@public/apiv2/HTTPUtils';
import { ProcessingSocket } from '@public/apiv2/sockets/ProcessingSocket';

import { loadMe } from './modules/auth/AuthStore';
import { loadDonations } from './modules/donations/DonationsStore';
import { loadProcessActions } from './modules/processing/ProcessActionsStore';
import * as Theming from './modules/theming/Theming';
import ProcessDonations from './pages/ProcessDonations';
import ReadDonations from './pages/ReadDonations';

import '../.design_system/generated/DesignSystem.css';
import '@spyrothon/sparx/style.css';

export default function App() {
  const canChangeDonations = usePermission('tracker.change_donation');
  const { theme, accent } = Theming.useThemeStore();

  const { APIV2_ROOT } = useConstants();

  React.useEffect(() => {
    setAPIRoot(APIV2_ROOT);
  }, [APIV2_ROOT]);

  useQuery('auth.me', () => APIClient.getMe(), {
    onSuccess: me => loadMe(me),
    staleTime: 5 * 60 * 1000,
  });

  React.useEffect(() => {
    const unsubActions = ProcessingSocket.on('processing_action', event => {
      loadDonations([event.donation]);
      loadProcessActions([event.action]);
    });

    const unsubNewDonations = ProcessingSocket.on('donation_received', event => {
      loadDonations([event.donation]);
    });

    const unsubUpdatedDonations = ProcessingSocket.on('donation_updated', event => {
      loadDonations([event.donation]);
    });

    return () => {
      unsubActions();
      unsubNewDonations();
      unsubUpdatedDonations();
    };
  }, []);

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
