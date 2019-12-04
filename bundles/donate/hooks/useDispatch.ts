import { Dispatch } from 'redux';
import { useDispatch } from 'react-redux';
import { Action } from '../Action';
import { store } from '../Store';

const useSafeDispatch = () => useDispatch<Dispatch<Action>>();

export type SafeDispatch = ReturnType<typeof useSafeDispatch>;

export default useSafeDispatch;
