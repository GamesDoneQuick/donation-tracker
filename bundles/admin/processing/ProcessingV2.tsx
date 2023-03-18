import * as React from 'react';
import { Route, Switch } from 'react-router';

import { usePermission } from '@public/api/helpers/auth';

import ProcessDonations from './ProcessDonations';
import ThemeProvider from './Theming';

import './Theming.mod.css';

export default function ProcessingV2({ rootPath }: { rootPath: string }) {
  const canChangeDonations = usePermission('tracker.change_donation');

  return (
    <ThemeProvider>
      <Switch>
        {canChangeDonations && (
          <Route path={`${rootPath}/v2/:eventId/processing/donations`} exact component={ProcessDonations} />
        )}
      </Switch>
    </ThemeProvider>
  );
}
