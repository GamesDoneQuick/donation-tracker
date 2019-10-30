import React from 'react';
import ReactDOM from 'react-dom';
import HTML5Backend from 'react-dnd-html5-backend';
import {DndProvider} from 'react-dnd';
import {Provider} from 'react-redux';
import {ConnectedRouter} from 'connected-react-router';
import {Route} from 'react-router';

import ErrorBoundary from 'ui/public/errorBoundary';


import App from './app';


window.AdminApp = function (props) {
  ReactDOM.render(
    <ErrorBoundary>
      <DndProvider backend={HTML5Backend}>
        <Provider store={App.store}>
          <ConnectedRouter history={App.history}>
            <Route path={window.ROOT_PATH} component={App}/>
          </ConnectedRouter>
        </Provider>
      </DndProvider>
    </ErrorBoundary>,
    document.getElementById("container")
  );
};
