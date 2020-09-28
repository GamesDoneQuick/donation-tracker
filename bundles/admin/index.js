import React from 'react';
import ReactDOM from 'react-dom';
import HTML5Backend from 'react-dnd-html5-backend';
import { DndProvider } from 'react-dnd';
import { Provider } from 'react-redux';
import { ConnectedRouter } from 'connected-react-router';
import { Redirect, Route, Switch } from 'react-router';

import ErrorBoundary from 'ui/public/errorBoundary';

import App from './app';
import Constants from '../common/Constants';
import { createTrackerStore } from '../public/api';

window.AdminApp = function (props) {
  function redirect({ location }) {
    return <Redirect to={location.pathname.replace(/\/\/+/g, '/')} />;
  }

  const store = createTrackerStore({ apiRoot: props.CONSTANTS.API_ROOT });

  ReactDOM.render(
    <ErrorBoundary>
      <DndProvider backend={HTML5Backend}>
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
      </DndProvider>
    </ErrorBoundary>,
    document.getElementById('container'),
  );
};
