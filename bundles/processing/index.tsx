import React from 'react';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { createRoot } from 'react-dom/client';
import { Provider } from 'react-redux';
import { setupListeners } from '@reduxjs/toolkit/query';

import Constants from '@common/Constants';
import { store } from '@public/apiv2/Store';
import ErrorBoundary from '@public/errorBoundary';

import App from './App';

import '@common/init';

window.AdminApp = function () {
  const root = createRoot(document.getElementById('container')!);
  setupListeners(store.dispatch);

  root.render(
    <ErrorBoundary>
      <DndProvider backend={HTML5Backend}>
        <Provider store={store}>
          <Constants.Provider value={JSON.parse(document.getElementById('CONSTANTS')!.textContent!)}>
            <App />
          </Constants.Provider>
        </Provider>
      </DndProvider>
    </ErrorBoundary>,
  );
};
