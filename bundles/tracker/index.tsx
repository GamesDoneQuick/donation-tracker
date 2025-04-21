import React from 'react';
import { createRoot } from 'react-dom/client';
import { Provider } from 'react-redux';

import Constants from '@common/Constants';
import { store } from '@public/apiv2/Store';
import ErrorBoundary from '@public/errorBoundary';
import ThemeProvider from '@uikit/ThemeProvider';

import AppWrapper from './App';

import '@common/init';

window.TrackerApp = () => {
  const container = document.getElementById('container');
  if (container == null) return;

  const root = createRoot(container);

  root.render(
    <Provider store={store}>
      <ThemeProvider>
        <ErrorBoundary>
          <Constants.Provider value={JSON.parse(document.getElementById('CONSTANTS')!.textContent!)}>
            <AppWrapper />
          </Constants.Provider>
        </ErrorBoundary>
      </ThemeProvider>
    </Provider>,
  );
};
