export type MaybeArray<T> = T | T[];

export function forceArray<T>(a: MaybeArray<T>): NonNullable<T>[] {
  return (Array.isArray(a) ? a : [a]).filter((m): m is NonNullable<T> => m != null);
}
