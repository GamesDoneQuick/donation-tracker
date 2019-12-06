import { Dispatch } from 'redux';
import { useDispatch } from 'react-redux';
import { Action } from '../Action';

const useSafeDispatch = () => useDispatch<Dispatch<Action>>();

export type SafeDispatch = ReturnType<typeof useSafeDispatch>;

export default useSafeDispatch;
