import React from 'react';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from 'react-query';
import { BrowserRouter } from 'react-router-dom';

import Constants from '@common/Constants';
import { createTrackerStore } from '@public/api';
import { setAPIRoot, setCSRFToken } from '@public/apiv2/HTTPUtils';
import ErrorBoundary from '@public/errorBoundary';

import { setAdminPath } from '@processing/modules/settings/PrimaryNavPopout';

import AdminV1Compat from './AdminV1Compat';
import App from './App';

import '@common/init';

window.AdminApp = function (props: any) {
  const store = createTrackerStore();
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
      },
    },
  });

  setCSRFToken(props.csrfToken);
  setAdminPath(props.ROOT_PATH);
  setAPIRoot(props.CONSTANTS.APIV2_ROOT);

  const root = createRoot(document.getElementById('container')!);

  root.render(
    <ErrorBoundary>
      <DndProvider backend={HTML5Backend}>
        <AdminV1Compat apiRoot={props.CONSTANTS.API_ROOT} store={store}>
          <QueryClientProvider client={queryClient}>
            <Constants.Provider value={props.CONSTANTS}>
              <BrowserRouter basename={props.ROOT_PATH}>
                <App />
              </BrowserRouter>
            </Constants.Provider>
          </QueryClientProvider>
        </AdminV1Compat>
      </DndProvider>
    </ErrorBoundary>,
  );
};
