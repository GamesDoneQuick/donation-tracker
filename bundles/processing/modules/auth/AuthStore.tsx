import create from 'zustand';
import { Me } from '@gamesdonequick/donation-tracker-api-types';

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
