import { useDispatch } from 'react-redux';

export type MaybeEmpty<T> = T extends void ? object : T;
export type MaybeObject<T> = T extends object ? T : never;
export type Dispatch = ReturnType<typeof useDispatch>;
