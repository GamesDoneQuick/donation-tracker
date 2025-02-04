import * as React from 'react';
import { Route, Routes } from 'react-router';

import { useConstants } from '@common/Constants';
import { useCSRFToken, usePermission } from '@public/api/helpers/auth';
import APIClient from '@public/apiv2/APIClient';
import { setRoot } from '@public/apiv2/reducers/trackerApi';
import { useAppDispatch } from '@public/apiv2/Store';

import { loadDonations } from './modules/donations/DonationsStore';
import { setEventTotalIfNewer } from './modules/event/EventTotalStore';
import useProcessingStore from './modules/processing/ProcessingStore';
import * as Theming from './modules/theming/Theming';
import ProcessDonations from './pages/ProcessDonations';
import ReadDonations from './pages/ReadDonations';
import { AppContainer } from './Theming';

import '../../design/generated/system.css';
import '@spyrothon/sparx/style.css';

export default function App() {
  const dispatch = useAppDispatch();
  const canViewDonationFeeds = usePermission('tracker.view_comments', 'tracker.view_donation', 'tracker.view_bid');
  const { processDonation } = useProcessingStore();
  const { theme, accent } = Theming.useThemeStore();

  const { APIV2_ROOT, PAGINATION_LIMIT } = useConstants();
  const csrfToken = useCSRFToken();

  React.useLayoutEffect(() => {
    dispatch(setRoot({ root: APIV2_ROOT, limit: PAGINATION_LIMIT, csrfToken }));
  }, [APIV2_ROOT, csrfToken, PAGINATION_LIMIT, dispatch]);

  React.useEffect(() => {
    const unsubActions = APIClient.sockets.processingSocket.on('processing_action', event => {
      loadDonations([event.donation]);
      if (event.action !== 'unprocessed') {
        processDonation(event.donation, event.action, false);
      }
    });

    const unsubNewDonations = APIClient.sockets.processingSocket.on('donation_received', event => {
      loadDonations([event.donation]);
      setEventTotalIfNewer(event.event_total, event.donation_count, new Date(event.posted_at).getTime());
    });

    return () => {
      unsubActions();
      unsubNewDonations();
    };
  }, [processDonation]);

  return (
    <AppContainer theme={theme} accent={accent}>
      <Routes>
        {canViewDonationFeeds && (
          <>
            <Route path="/v2/:eventId/processing/donations" element={<ProcessDonations />} />
            <Route path="/v2/:eventId/processing/read" element={<ReadDonations />} />
          </>
        )}
      </Routes>
    </AppContainer>
  );
}
