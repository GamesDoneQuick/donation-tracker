import React from 'react';
import ReactDOM from 'react-dom';
import HTML5Backend from 'react-dnd-html5-backend';
import { DndProvider } from 'react-dnd';
import { Provider } from 'react-redux';
import { ConnectedRouter } from 'connected-react-router';
import { Redirect, Route, Switch } from 'react-router';

import ErrorBoundary from 'ui/public/errorBoundary';

import App from './app';
import Globals from '../common/Globals';

window.AdminApp = function(props) {
  function redirect({ location }) {
    return <Redirect to={location.pathname.replace(/\/\/+/g, '/')} />;
  }

  ReactDOM.render(
    <ErrorBoundary>
      <DndProvider backend={HTML5Backend}>
        <Provider store={App.store}>
          <Globals.Provider value={props.CONSTANTS}>
            <ConnectedRouter history={App.history}>
              <Switch>
                <Route exact strict path="(.*//+.*)" render={redirect} />
                <Route path={props.ROOT_PATH} component={App} />
              </Switch>
            </ConnectedRouter>
          </Globals.Provider>
        </Provider>
      </DndProvider>
    </ErrorBoundary>,
    document.getElementById('container'),
  );
};
