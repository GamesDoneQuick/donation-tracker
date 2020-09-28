export default function freeze(obj) {
  if (Object.isFrozen(obj)) return obj;

  const propNames = Object.getOwnPropertyNames(obj);

  propNames.forEach(function (name) {
    const prop = obj[name];

    if (typeof prop === 'object' && prop !== null) {
      obj[name] = freeze(prop);
    }
  });

  return Object.freeze(obj);
}
