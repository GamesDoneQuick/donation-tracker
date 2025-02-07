import React from 'react';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';

import Constants from '@common/Constants';
import APIClient from '@public/apiv2/APIClient';
import { setAPIRoot, setCSRFToken } from '@public/apiv2/HTTPUtils';
import { store } from '@public/apiv2/Store';
import ErrorBoundary from '@public/errorBoundary';

import { setAdminPath } from '@processing/modules/settings/PrimaryNavPopout';

import App from './App';

import '@common/init';

window.AdminApp = function (props: any) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
      },
    },
  });

  setCSRFToken(props.csrfToken);
  setAdminPath(props.ROOT_PATH);
  APIClient.sockets.setSocketRoot(`${props.TRACKER_PATH}/ws/`);
  setAPIRoot(props.CONSTANTS.APIV2_ROOT);

  const root = createRoot(document.getElementById('container')!);

  root.render(
    <ErrorBoundary>
      <DndProvider backend={HTML5Backend}>
        <Provider store={store}>
          <QueryClientProvider client={queryClient}>
            <Constants.Provider value={props.CONSTANTS}>
              <BrowserRouter basename={props.ROOT_PATH}>
                <App />
              </BrowserRouter>
            </Constants.Provider>
          </QueryClientProvider>
        </Provider>
      </DndProvider>
    </ErrorBoundary>,
  );
};
