import * as React from 'react';

export default function useAnimationFrame<T>(callback: () => T, callbackDeps: unknown[] = []): T {
  const [result] = React.useState<{ current: T }>(() => ({ current: callback() }));
  const rafId = React.useRef<number>();

  React.useEffect(() => {
    function loop() {
      rafId.current != null && cancelAnimationFrame(rafId.current);
      result.current = callback();
      rafId.current = requestAnimationFrame(loop);
    }

    rafId.current = requestAnimationFrame(loop);
    return () => {
      rafId.current != null && cancelAnimationFrame(rafId.current);
    };
    // ESLint can't know what we want here because `result` is a ref, and we
    // don't know what `callbackDeps` is.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, callbackDeps);

  return result.current;
}
