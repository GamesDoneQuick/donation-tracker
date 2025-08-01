import React from 'react';
import { Route, Routes } from 'react-router';
import { BrowserRouter } from 'react-router-dom';

import { useConstants } from '@common/Constants';
import { usePermission, useTrackerInit } from '@public/apiv2/hooks';
import NotFound from '@public/notFound';

import * as Theming from './modules/theming/Theming';
import ProcessDonations from './pages/ProcessDonations';
import ReadDonations from './pages/ReadDonations';
import { AppContainer } from './Theming';

import '../../design/generated/system.css';
import '../../design/generated/fontImports.css';
import '@faulty/gdq-design/style.css';

export default function App() {
  const canViewDonationFeeds = usePermission('tracker.view_comments', 'tracker.view_donation', 'tracker.view_bid');
  const { theme, accent } = Theming.useThemeStore();
  const { ROOT_PATH } = useConstants();

  useTrackerInit();

  return (
    <AppContainer theme={theme} accent={accent}>
      <BrowserRouter basename={ROOT_PATH}>
        <Routes>
          {canViewDonationFeeds && (
            <>
              <Route path="/v2/:eventId/processing/donations" element={<ProcessDonations />} />
              <Route path="/v2/:eventId/processing/read" element={<ReadDonations />} />
            </>
          )}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </AppContainer>
  );
}
