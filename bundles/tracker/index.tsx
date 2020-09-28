import * as React from 'react';
import * as ReactDOM from 'react-dom';
import { Provider } from 'react-redux';

import ErrorBoundary from '../public/errorBoundary';
import ThemeProvider from '../uikit/ThemeProvider';
import AppWrapper from './App';
import { createTrackerStore } from './Store';
import { createRouterUtils, RouterUtils } from './router/RouterUtils';

// TODO: Migrate all page-load props to API calls. Currently these props
// are just being proxied through to `AppWrapper` which decides what props
// it should expect, and is only used for the `/donate` page.
window.TrackerApp = (props: any) => {
  const store = createTrackerStore({ apiRoot: props.CONSTANTS.API_ROOT });
  const routerUtils = createRouterUtils({ rootPath: props.ROOT_PATH });

  ReactDOM.render(
    <Provider store={store}>
      <ThemeProvider>
        <ErrorBoundary>
          <RouterUtils.Provider value={routerUtils}>
            <AppWrapper {...props} />
          </RouterUtils.Provider>
        </ErrorBoundary>
      </ThemeProvider>
    </Provider>,
    document.getElementById('container'),
  );
};
