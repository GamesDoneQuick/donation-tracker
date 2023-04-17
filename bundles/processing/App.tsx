import React from 'react';
import { Route, Switch } from 'react-router';
import loadable from '@loadable/component';

import { useConstants } from '@common/Constants';
import { setAPIRoot } from '@public/apiv2/HTTPUtils';

const ProcessingV2 = loadable(() => import('./ProcessingV2' /* webpackChunkName: 'processingV2' */));

function App() {
  const { APIV2_ROOT } = useConstants();

  React.useEffect(() => {
    setAPIRoot(APIV2_ROOT);
  }, [APIV2_ROOT]);

  return (
    <Switch>
      <Route component={ProcessingV2} />
    </Switch>
  );
}

export default App;
