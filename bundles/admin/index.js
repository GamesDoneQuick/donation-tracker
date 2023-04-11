import React from 'react';
import { ConnectedRouter } from 'connected-react-router';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Provider } from 'react-redux';
import { Redirect, Route, Switch } from 'react-router';

import Constants from '@common/Constants';
import { createTrackerStore } from '@public/api';
import V2HTTPUtils from '@public/apiv2/HTTPUtils';
import ErrorBoundary from '@public/errorBoundary';

import App from './app';

import '@common/init';

window.AdminApp = function (props) {
  function redirect({ location }) {
    return <Redirect to={location.pathname.replace(/\/\/+/g, '/')} />;
  }

  const store = createTrackerStore();
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
      },
    },
  });

  V2HTTPUtils.setCSRFToken(props.csrfToken);

  const root = createRoot(document.getElementById('container'));

  root.render(
    <ErrorBoundary>
      <DndProvider backend={HTML5Backend}>
        <QueryClientProvider client={queryClient}>
          <Provider store={store}>
            <Constants.Provider value={props.CONSTANTS}>
              <ConnectedRouter history={store.history}>
                <Switch>
                  <Route exact strict path="(.*//+.*)" render={redirect} />
                  <Route path={props.ROOT_PATH} component={App} />
                </Switch>
              </ConnectedRouter>
            </Constants.Provider>
          </Provider>
        </QueryClientProvider>
      </DndProvider>
    </ErrorBoundary>,
  );
};
