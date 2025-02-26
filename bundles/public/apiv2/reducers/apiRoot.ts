import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface RootShape {
  root: string;
  limit: number;
  csrfToken: string;
}

export const apiRoot = createSlice({
  name: 'apiRoot',
  initialState: (): RootShape => ({ root: '', limit: 0, csrfToken: '' }),
  reducers: {
    setRoot(_, action: PayloadAction<RootShape>) {
      return action.payload;
    },
  },
});

export const { setRoot } = apiRoot.actions;

export function getRoot(api: { getState: () => unknown }): string | undefined {
  return (api.getState() as { apiRoot?: RootShape })?.apiRoot?.root;
}
