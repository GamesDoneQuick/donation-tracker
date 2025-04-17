import { create } from 'zustand';

import { Me } from '@public/apiv2/APITypes';

interface AuthStoreState {
  me: Me | null;
}

const useAuthStore = create<AuthStoreState>()(() => ({
  me: null,
}));

export default useAuthStore;

export function useMe() {
  return useAuthStore(state => state.me);
}

export function loadMe(me: Me) {
  useAuthStore.setState({ me });
}

export function logout() {
  useAuthStore.setState({ me: null });
}
