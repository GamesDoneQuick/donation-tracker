import { useDispatch } from 'react-redux';
import { Action } from 'redux';
import { ThunkDispatch } from 'redux-thunk';

import { createTrackerStore } from '.';

type StoreState = ReturnType<typeof createTrackerStore>;

const useSafeDispatch = () => useDispatch<ThunkDispatch<StoreState, never, Action<any>>>();

export type SafeDispatch = ReturnType<typeof useSafeDispatch>;

export default useSafeDispatch;
