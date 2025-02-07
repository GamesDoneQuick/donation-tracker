import { useDispatch, useSelector } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';

import { apiRootSlice, pageInfo, trackerApi } from '@public/apiv2/reducers/trackerApi';

export const store = configureStore({
  reducer: {
    [trackerApi.reducerPath]: trackerApi.reducer,
    pageInfo: pageInfo.reducer,
    apiRoot: apiRootSlice.reducer,
  },
  middleware: getDefaultMiddleware => getDefaultMiddleware({ serializableCheck: false }).concat(trackerApi.middleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
export const useAppDispatch = useDispatch.withTypes<AppDispatch>();
export const useAppSelector = useSelector.withTypes<RootState>();
