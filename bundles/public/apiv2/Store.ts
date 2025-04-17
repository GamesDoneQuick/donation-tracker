import { useDispatch, useSelector } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';

import { apiRoot } from '@public/apiv2/reducers/apiRoot';
import { socketsReducer, socketsReducerPath } from '@public/apiv2/reducers/sockets';
import { trackerApi } from '@public/apiv2/reducers/trackerApi';
import { pageInfoReducer, pageInfoReducerPath } from '@public/apiv2/reducers/trackerBaseApi';

export const store = configureStore({
  reducer: {
    [apiRoot.reducerPath]: apiRoot.reducer,
    [trackerApi.reducerPath]: trackerApi.reducer,
    // internal actions only
    [pageInfoReducerPath]: pageInfoReducer,
    [socketsReducerPath]: socketsReducer,
  },
  middleware: getDefaultMiddleware => getDefaultMiddleware({ serializableCheck: false }).concat(trackerApi.middleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
export const useAppDispatch = useDispatch.withTypes<AppDispatch>();
export const useAppSelector = useSelector.withTypes<RootState>();
