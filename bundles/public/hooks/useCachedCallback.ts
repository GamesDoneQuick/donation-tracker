import React from 'react';
import invariant from 'invariant';
import isObject from 'lodash/isObject';

function JSONKey(...args: any[]): string {
  return args.length > 1 || isObject(args[0]) || args[0] == null ? JSON.stringify(args) : args[0].toString();
}

// use this instead of useCallback when you need pre-bound arguments that differ in a loop
//
// the default `key` function uses the JSON representation of the args as an array (with all the normal JSON.stringify
// caveats), or just the string value if there is only one primitive arg
//
// example:
//
// function Example({deleteThing, listOfThings}) {
//   const deleteThingCached = useCachedCallback(id => deleteThing(id), [deleteThing]);
//   return (
//     <div>
//       {listOfThings.map(thing =>
//         <div key={thing.id}>
//           A thing is named `{thing.name}`.
//           <button onClick={deleteThingCached(thing.id)}>Delete</button>
//         </div>
//       )}
//     </div>
//   )
// }
//
// if additional arguments are going to come in from the children, you can use the spread syntax
//
// example:
//
// useCachedCallback((id, ...args) => someComplexCallback(id, ...args), [someComplexCallback])
//
// this function follows the same form as most use* hooks, so you can add it to your eslint rules, like so:
//
// "react-hooks/exhaustive-deps": [
//   "error",
//   {
//     "additionalHooks": "useCachedCallback"
//   }
// ],
//

type MemoDict<R1> = {
  [k: string]: () => R1;
};

export function useCachedCallback<R1>(callback: (...args: any[]) => R1, dependencies: any[], key = JSONKey) {
  /* eslint-disable react-hooks/exhaustive-deps */
  const memo = React.useMemo<MemoDict<R1>>(() => ({}), dependencies);
  const keyFunc = React.useRef(key);
  return React.useCallback(
    (...bound: any[]) => {
      const paramKey = keyFunc.current(...bound);
      if (TRACKER_DEBUG) {
        const paramKey2 = key(...bound);
        invariant(
          paramKey === paramKey2,
          `Key function is not returning consistent values: ${paramKey} !== ${paramKey2}`,
        );
      }
      return (memo[paramKey] = memo[paramKey] || ((...args) => callback(...bound, ...args)));
    },
    [memo],
  );
  /* eslint-enable react-hooks/exhaustive-deps */
}
