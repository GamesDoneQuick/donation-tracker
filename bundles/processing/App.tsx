import React from 'react';
import Loadable from 'react-loadable';
import { Route, Switch } from 'react-router';

import { useConstants } from '@common/Constants';
import Loading from '@common/Loading';
import { setAPIRoot } from '@public/apiv2/HTTPUtils';

const ProcessingV2 = Loadable({
  loader: () => import('./ProcessingV2' /* webpackChunkName: 'processingV2' */),
  loading: function LoadingSpinner() {
    return <Loading />;
  },
});

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
