import * as React from 'react';
import { Provider } from 'react-redux';
import { AnyAction, applyMiddleware, createStore, Store } from 'redux';
import { render } from '@testing-library/react';

import { setAPIRoot } from '../bundles/tracker/Endpoints';
import { combinedReducer, StoreState } from '../bundles/tracker/Store';

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

interface Children {
  children: React.ReactNode;
}

function createMockReactClass(Klass: any) {
  return class MockClass extends React.Component<Children> {
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

let emptyState: StoreState;

let store: Store<StoreState>;
const MOCKED_STATE = Symbol('MOCKED_STATE');

const mockedThunk = (_: any) => (next: (action: any) => any) => (action: any) => {
  if (typeof action === 'function') {
    // TODO: display warning for unknown thunks
  } else {
    return next(action);
  }
};

beforeEach(() => {
  store = createStore((state: StoreState = emptyState, action: AnyAction) => {
    if (action.type === MOCKED_STATE) {
      return action.newState;
    } else {
      return combinedReducer(state, action);
    }
  }, applyMiddleware(mockedThunk));
  emptyState = store.getState();
});

export function mockState(initialState: Partial<StoreState>): void {
  store.dispatch({ type: MOCKED_STATE, newState: { ...emptyState, ...initialState } });
}

export function renderWithState(...[element, options]: Parameters<typeof render>): ReturnType<typeof render> {
  return render(<Provider store={store}>{element}</Provider>, options);
}

beforeEach(() => {
  setAPIRoot('http://testserver/');
});
