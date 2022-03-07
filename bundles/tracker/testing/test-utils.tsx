import * as React from 'react';
import { createStore } from 'redux';
import { Provider } from 'react-redux';
import { render } from '@testing-library/react';

import { combinedReducer, StoreState } from '@tracker/Store';
import ThemeProvider from '@uikit/ThemeProvider';

type WrapProps = {
  children: React.ReactNode;
  store: ReturnType<typeof createStore>;
};

const Wrap = ({ children, store }: WrapProps) => {
  return (
    <ThemeProvider>
      <Provider store={store}>{children}</Provider>
    </ThemeProvider>
  );
};

function customCreateStore(initialState: Partial<StoreState> = {}) {
  return createStore(combinedReducer, initialState);
}

type RenderOptions = {
  initialState?: Partial<StoreState>;
  store?: ReturnType<typeof createStore>;
};

function customRender(component: React.ReactElement, { initialState, store }: RenderOptions = {}) {
  if (store == null) {
    store = customCreateStore(initialState);
  }

  return {
    ...render(<Wrap store={store}>{component}</Wrap>),
    // adding `store` to the returned utilities to allow us to reference
    // it in our tests.
    store,
  };
}

// re-export everything
export * from '@testing-library/react';
// override render method
export { customRender as render, customCreateStore as createStore };
