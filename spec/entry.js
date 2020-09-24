import './Suite';
import './matchers';

const modules = require.context('../bundles', true, /(Spec|\.spec)\.[jt]sx?$/);
modules.keys().forEach(modules);
