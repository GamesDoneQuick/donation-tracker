import * as React from 'react';
import { createRoot } from 'react-dom/client';
import { Provider } from 'react-redux';

import Constants from '@common/Constants';
import ErrorBoundary from '@public/errorBoundary';
import ThemeProvider from '@uikit/ThemeProvider';

import DonateInitializer from './donation/components/DonateInitializer';
import AppWrapper from './App';
import { createTrackerStore } from './Store';

import '@common/init';

// TODO: Migrate all page-load props to API calls. Currently these props
// are just being proxied through to `AppWrapper` which decides what props
// it should expect, and is only used for the `/donate` page.
window.TrackerApp = (props: any) => {
  const store = createTrackerStore();

  const container = document.getElementById('container');
  if (container == null) return;

  const root = createRoot(container);

  // TODO: This isn't perfectly accurate, but the donation page is the only one
  // that loads props from the static HTML anyway, so any check is sufficient here.
  const hasDonationInitializerProps = 'incentives' in props;

  root.render(
    <Provider store={store}>
      <ThemeProvider>
        <ErrorBoundary>
          <Constants.Provider value={props.CONSTANTS}>
            <AppWrapper {...props} />
            {/* TODO: This is simpler than passing `props` through the router
              components until we reach the /donate path, but it should be
              refactored to not be dependent on these props, or use some
              global context instead. */}
            {hasDonationInitializerProps ? <DonateInitializer {...props} /> : null}
          </Constants.Provider>
        </ErrorBoundary>
      </ThemeProvider>
    </Provider>,
  );
};
