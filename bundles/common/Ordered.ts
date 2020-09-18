import { Ordered, Subordered } from './Models';
import memoize from 'memoize-one';
import { fullKey, isSubordered } from './Util';

export const sortItems = memoize((models: Ordered[]) => {
  const unsorted: Ordered[] = models.slice();

  function unorderedCompare(a: Ordered, b: Ordered): number {
    if (b.fields.order === null) {
      return fullKey(a).localeCompare(fullKey(b));
    } else {
      return 1;
    }
  }

  function soCompare(a: Subordered, b: Ordered | Subordered): number {
    if (isSubordered(b)) {
      if (a.fields.suborder < b.fields.suborder) {
        return -1;
      } else if (a.fields.suborder > b.fields.suborder) {
        return 1;
      }
      throw new Error('items could not be totally ordered');
    } else {
      // same order, but b is not subordered so this always comes after
      return 1;
    }
  }

  return unsorted.sort((a, b) => {
    if (a.fields.order === null) {
      return unorderedCompare(a, b);
    } else if (b.fields.order === null) {
      return -unorderedCompare(b, a);
    } else if (a.fields.order < b.fields.order) {
      return -1;
    } else if (a.fields.order > b.fields.order) {
      return 1;
    } else if (isSubordered(a)) {
      return soCompare(a, b);
    } else if (isSubordered(b)) {
      return -soCompare(b, a);
    }
    throw new Error('items could not be totally ordered');
  });
});
