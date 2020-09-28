import { Model, Ordered, Subordered } from './Models';

interface KeyFunction {
  (...args: any[]): string;
}

function ArrayIdentity(...args: any[]) {
  return args.join('-');
}

interface MemoCache {
  [key: string]: (...args: any[]) => any;
}

export function memoizeCallback(callback: (...args: any[]) => any, key: KeyFunction = ArrayIdentity) {
  const memo: MemoCache = {};
  return function (...curried: any[]) {
    const paramKey = key(...curried);
    return (memo[paramKey] = memo[paramKey] || callback.bind(null, ...curried));
  };
}

export function isSubordered(model: Model | Ordered | Subordered): model is Subordered {
  return Object.prototype.hasOwnProperty.call(model.fields, 'suborder');
}

export function isOrdered(model: Model | Ordered): model is Ordered {
  return Object.prototype.hasOwnProperty.call(model.fields, 'order');
}

export function fullKey(item: Model): string {
  return `${item.model}-${item.pk}`;
}
