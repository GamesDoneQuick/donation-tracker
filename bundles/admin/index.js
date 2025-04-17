import React from 'react';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { createRoot } from 'react-dom/client';
import { Provider } from 'react-redux';

import Constants from '@common/Constants';
import V2HTTPUtils from '@public/apiv2/HTTPUtils';
import { store } from '@public/apiv2/Store';
import ErrorBoundary from '@public/errorBoundary';

import App from './app';

import '@common/init';

function Routes(props) {
  return (
    <ErrorBoundary>
      <DndProvider backend={HTML5Backend}>
        <Provider store={store}>
          <Constants.Provider value={props.CONSTANTS}>
            <App rootPath={props.ROOT_PATH} />
          </Constants.Provider>
        </Provider>
      </DndProvider>
    </ErrorBoundary>
  );
}

window.AdminApp = function (props) {
  V2HTTPUtils.setCSRFToken(props.csrfToken);

  const root = createRoot(document.getElementById('container'));

  root.render(<Routes {...props} />);
};
