import { useDispatch, useSelector } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';

import { apiRoot } from '@public/apiv2/reducers/apiRoot';
import { socketsReducer, socketsReducerPath } from '@public/apiv2/reducers/sockets';
import { trackerApi } from '@public/apiv2/reducers/trackerApi';
import { pageInfoReducer, pageInfoReducerPath } from '@public/apiv2/reducers/trackerBaseApi';

const middlewares = [trackerApi.middleware];

if (TRACKER_REDUX_LOGGING) {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { createLogger } = require('redux-logger');
  middlewares.push(createLogger({ actionTransformer: JSON.stringify }));
}

export const store = configureStore({
  reducer: {
    [apiRoot.reducerPath]: apiRoot.reducer,
    [trackerApi.reducerPath]: trackerApi.reducer,
    // internal actions only
    [pageInfoReducerPath]: pageInfoReducer,
    [socketsReducerPath]: socketsReducer,
  },
  middleware: getDefaultMiddleware => getDefaultMiddleware({ serializableCheck: false }).concat(middlewares),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
export const useAppDispatch = useDispatch.withTypes<AppDispatch>();
export const useAppSelector = useSelector.withTypes<RootState>();
