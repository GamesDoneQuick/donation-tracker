export type MaybePromise<T> = PromiseLike<T> | T;

export type MaybeArray<T> = T | T[];
export type Flatten<T> = T extends Array<infer E> ? E : T;
export type ForceArray<T> = Array<Flatten<T>>;

export function forceArray<T>(a: MaybeArray<T>): NonNullable<T>[] {
  return (Array.isArray(a) ? a : [a]).filter((m): m is NonNullable<T> => m != null);
}

export type DataProps<T> = T & { [key: `data-${string}`]: string };

export function dataProps<T>(props: DataProps<T>): { [key: `data-${string}`]: string } {
  return Object.fromEntries(Object.entries(props).filter(([k]) => k.startsWith('data-')));
}
