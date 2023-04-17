import * as React from 'react';
import { Provider, useDispatch } from 'react-redux';

import actions from '@public/api/actions';

import { setAPIRoot } from '@tracker/Endpoints';

function V1Init({ apiRoot }) {
  const dispatch = useDispatch();

  React.useEffect(() => {
    setAPIRoot(apiRoot);
    dispatch(actions.singletons.fetchMe());
  }, [dispatch, apiRoot]);

  return null;
}

/**
 * This component manages everything related to API and Admin v1 setup and
 * compatibility, allowing v2 components to use things like `usePermission`
 * without needing them to be re-written immediately.
 *
 * This component should be removed once V1 is no longer needed.
 *
 * @returns null
 */
export default function AdminV1Compat({ apiRoot, store, children }) {
  return (
    <Provider store={store}>
      <V1Init apiRoot={apiRoot} />
      {React.Children.only(children)}
    </Provider>
  );
}
