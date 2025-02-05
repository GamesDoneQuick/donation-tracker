import './Suite';
import './matchers';

const modules = require.context('../bundles', true, /(Spec|\.spec)\.[jt]sx?$/);
modules.keys().forEach(modules);

let consoleLogs = [];

function failTest(...args) {
  if (args[1] !== 'ReactNumeric') {
    consoleLogs.push([...args]);
  }
  // eslint-disable-next-line no-console
  console.log(...args);
}

beforeEach(() => {
  consoleLogs = [];
  spyOn(console, 'warn').and.callFake(failTest);
  spyOn(console, 'error').and.callFake(failTest);
});

afterEach(() => {
  expect(consoleLogs).toEqual([]);
});
