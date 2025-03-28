import React from 'react';
import { Route, Routes } from 'react-router';
import { Text } from '@faulty/gdq-design';

import APIClient from '@public/apiv2/APIClient';
import { usePermission } from '@public/apiv2/helpers/auth';
import { useTrackerInit } from '@public/apiv2/hooks';
import { useDonationGroupsQuery, useMeQuery } from '@public/apiv2/reducers/trackerApi';

import useDonationGroupsStore from '@processing/modules/donation-groups/DonationGroupsStore';

import { loadDonations, syncDonationGroups } from './modules/donations/DonationsStore';
import { setEventTotalIfNewer } from './modules/event/EventTotalStore';
import useProcessingStore from './modules/processing/ProcessingStore';
import * as Theming from './modules/theming/Theming';
import ProcessDonations from './pages/ProcessDonations';
import ReadDonations from './pages/ReadDonations';
import { AppContainer } from './Theming';

import '../../design/generated/system.css';
import '../../design/generated/fontImports.css';
import '@faulty/gdq-design/style.css';

export default function App() {
  const { isLoading: meLoading } = useMeQuery();
  const canViewDonationFeeds = usePermission('tracker.view_comments', 'tracker.view_donation', 'tracker.view_bid');
  const { processDonation } = useProcessingStore();
  const { theme, accent } = Theming.useThemeStore();

  const { data: groups, refetch: refetchGroups } = useDonationGroupsQuery();
  const { syncDonationGroupsWithServer } = useDonationGroupsStore();

  useTrackerInit();

  React.useEffect(() => {
    const unsubActions = APIClient.sockets.processingSocket.on('processing_action', event => {
      if (event.donation) {
        loadDonations([event.donation]);
        if (event.action !== 'unprocessed') {
          processDonation(event.donation, event.action, false);
        }
      } else if (event.group) {
        // TODO: sledgehammer, put this is the API itself when we can
        refetchGroups()
          .unwrap()
          .then(groups => {
            if (event.action === 'group_deleted') {
              syncDonationGroups(groups);
            }
          });
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
  }, [processDonation, refetchGroups]);

  React.useEffect(() => {
    if (groups) {
      syncDonationGroupsWithServer(groups);
    }
  }, [groups, syncDonationGroupsWithServer]);

  return (
    <AppContainer theme={theme} accent={accent}>
      <Routes>
        {canViewDonationFeeds && (
          <>
            <Route path="/v2/:eventId/processing/donations" element={<ProcessDonations />} />
            <Route path="/v2/:eventId/processing/read" element={<ReadDonations />} />
          </>
        )}
        {!meLoading && (
          <Route path="*" element={<Text>That page either does not exist or you do not have access to it.</Text>} />
        )}
      </Routes>
    </AppContainer>
  );
}
