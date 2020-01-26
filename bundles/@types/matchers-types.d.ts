declare namespace jasmine {
  interface Matchers<T> {
    toExist(): boolean;
  }
  interface ArrayLikeMatchers<T> {
    toHaveLength(expected: number): boolean;
  }
}
