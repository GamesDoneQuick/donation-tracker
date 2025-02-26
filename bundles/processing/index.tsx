import React from 'react';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { createRoot } from 'react-dom/client';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { setupListeners } from '@reduxjs/toolkit/query';

import Constants from '@common/Constants';
import { store } from '@public/apiv2/Store';
import ErrorBoundary from '@public/errorBoundary';

import { setAdminPath } from '@processing/modules/settings/PrimaryNavPopout';

import App from './App';

import '@common/init';

window.AdminApp = function (props: any) {
  setAdminPath(props.ROOT_PATH);

  const root = createRoot(document.getElementById('container')!);
  setupListeners(store.dispatch);

  root.render(
    <ErrorBoundary>
      <DndProvider backend={HTML5Backend}>
        <Provider store={store}>
          <Constants.Provider value={props.CONSTANTS}>
            <BrowserRouter basename={props.ROOT_PATH}>
              <App />
            </BrowserRouter>
          </Constants.Provider>
        </Provider>
      </DndProvider>
    </ErrorBoundary>,
  );
};
