import React from 'react';
import ReactDOM from 'react-dom';
import {Route} from 'react-router';
import {Provider} from 'react-redux';
import {ConnectedRouter} from 'react-router-redux';

import ErrorBoundary from 'ui/public/errorBoundary';
import ajaxSetup from 'ui/public/ajaxsetup';

import App from './app';
import DevTools from '../devtools';

if (__DEVTOOLS__) {
  window.store = App.store;
}

window.AdminApp = function (props) {
  ajaxSetup();
  ReactDOM.render(
    <ErrorBoundary>
      <Provider store={App.store}>
        <React.Fragment>
          <ConnectedRouter history={App.history}>
            <React.Fragment>
              <Route path={window.ROOT_PATH} component={App}/>
            </React.Fragment>
          </ConnectedRouter>
          {__DEVTOOLS__ && false ? <DevTools/> : null}
        </React.Fragment>
      </Provider>
    </ErrorBoundary>,
    document.getElementById("container"));
};
