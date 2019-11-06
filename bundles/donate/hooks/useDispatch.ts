import { useDispatch } from 'react-redux';
import { Action } from '../Action';
import { store } from '../Store';

const useSafeDispatch = () => useDispatch<typeof store.dispatch>();

export default useSafeDispatch;
