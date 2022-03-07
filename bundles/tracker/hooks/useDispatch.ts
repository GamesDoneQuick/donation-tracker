import { useDispatch } from 'react-redux';
import { ThunkDispatch } from 'redux-thunk';

import { Action } from '@tracker/Action';
import { StoreState } from '@tracker/Store';

const useSafeDispatch = () => useDispatch<ThunkDispatch<StoreState, never, Action>>();

export type SafeDispatch = ReturnType<typeof useSafeDispatch>;

export default useSafeDispatch;
