import { useDispatch } from 'react-redux';
import { Action } from '../Action';
import { store } from '../Reducer';

const useSafeDispatch = () => useDispatch<typeof store.dispatch>();

export default useSafeDispatch;
