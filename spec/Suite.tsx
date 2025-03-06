import React from 'react';

import './matchers';

let componentFakes: any[] = [];
let oldCreateElement: typeof React.createElement;

beforeEach(function () {
  oldCreateElement = React.createElement.bind(React);
  componentFakes = [];

  // @ts-ignore
  spyOn(React, 'createElement').and.callFake(function (type, props, ...children) {
    const fake = componentFakes.find(f => f.componentClass === type);
    if (fake) {
      type = fake.replacementClass;
    }
    return oldCreateElement(type, props, ...children);
  });
});

function name(klass: any) {
  return klass.displayName || klass.name || klass.toString();
}

function createMockReactClass(Klass: any) {
  return class MockClass extends React.Component<React.PropsWithChildren> {
    static displayName = `Mock${name(Klass)}`;
    static propTypes = { ...Klass.propTypes };
    static contextTypes = { ...Klass.contextTypes };

    render() {
      return <div>{this.props.children}</div>;
    }
  };
}

function createWrappedReactClass(Klass: any) {
  return class WrappedClass extends React.Component {
    static displayName = `Mock${name(Klass)}`;
    static propTypes = { ...Klass.propTypes };
    static contextTypes = { ...Klass.contextTypes };

    render() {
      return oldCreateElement(Klass, this.props);
    }
  };
}

export function mockComponent(componentClass: any): ReturnType<typeof createMockReactClass> {
  const alreadyMocked = componentFakes.find(cf => cf.componentClass === componentClass);
  expect(alreadyMocked).toBeUndefined('This component has already been replaced');
  const fakeComponentClass = createMockReactClass(componentClass);

  componentFakes.push({ componentClass: componentClass, replacementClass: fakeComponentClass });

  return fakeComponentClass;
}

export function wrapComponent(componentClass: any): ReturnType<typeof createWrappedReactClass> {
  const alreadyMocked = componentFakes.find(cf => cf.componentClass === componentClass);
  expect(alreadyMocked).toBeUndefined('This component has already been replaced');
  const wrappedComponentClass = createWrappedReactClass(componentClass);

  componentFakes.push({ componentClass: componentClass, replacementClass: wrappedComponentClass });

  return wrappedComponentClass;
}
