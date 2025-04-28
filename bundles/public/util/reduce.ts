export function sum(a: number, b: number) {
  return a + b;
}

export function concat<T>(a: T[], b: T[]) {
  return [...a, ...b];
}
