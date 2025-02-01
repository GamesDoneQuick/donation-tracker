/* eslint-disable @typescript-eslint/no-unused-vars */
// It's mad about the T but it needs to match the other namespace in jasmine

declare namespace jasmine {
  interface Matchers<T> {
    toExist(): boolean;
  }
  interface ArrayLikeMatchers<T> {
    toHaveLength(expected: number): boolean;
  }
}
