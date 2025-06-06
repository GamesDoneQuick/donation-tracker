import type { Draft } from 'immer';

export type MaybePromise<T> = PromiseLike<T> | T;

export type MaybeArray<T> = T | T[] | null | undefined;
export type Flatten<T> = T extends Array<infer E> ? E : T;
// doesn't necessarily work as expected on nested arrays
export type ForceArray<T> = Array<Flatten<T>>;

export function forceArray<T>(a: MaybeArray<T>): Array<NonNullable<T>> {
  return (Array.isArray(a) ? a : [a]).filter((m): m is NonNullable<T> => m != null);
}

export function hasItems<T>(a: T[] | undefined): a is T[] {
  return (a?.length ?? 0) > 0;
}

export type MaybeDrafted<T> = T | Draft<T>;

export type DataProps<T> = T & { [key: `data-${string}`]: string };

export function dataProps<T>(props: DataProps<T>): { [key: `data-${string}`]: string } {
  return Object.fromEntries(Object.entries(props).filter(([k]) => k.startsWith('data-')));
}
