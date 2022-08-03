import * as React from 'react';
import * as ReactDOM from 'react-dom';
import { Provider } from 'react-redux';

import Constants from '@common/Constants';
import ErrorBoundary from '@public/errorBoundary';
import ThemeProvider from '@uikit/ThemeProvider';

import AppWrapper from './App';
import { createTrackerStore } from './Store';

import '@common/init';

// TODO: Migrate all page-load props to API calls. Currently these props
// are just being proxied through to `AppWrapper` which decides what props
// it should expect, and is only used for the `/donate` page.
window.TrackerApp = (props: any) => {
  const store = createTrackerStore();

  ReactDOM.render(
    <Provider store={store}>
      <ThemeProvider>
        <ErrorBoundary>
          <Constants.Provider value={props.CONSTANTS}>
            <AppWrapper {...props} />
          </Constants.Provider>
        </ErrorBoundary>
      </ThemeProvider>
    </Provider>,
    document.getElementById('container'),
  );
};
