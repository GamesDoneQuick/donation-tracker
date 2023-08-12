import create from 'zustand';

interface EventTotalStoreState {
  updatedAt: number;
  total: number;
  donationCount: number;
}

const useEventTotalStore = create<EventTotalStoreState>()(() => ({
  updatedAt: 0,
  total: 0,
  donationCount: 0,
}));

export default useEventTotalStore;

/**
 * Update the current event total, but only if the updatedAt timestamp
 * is newer than the store's current last updatedAt value.
 */
export function setEventTotalIfNewer(total: number, donationCount: number, updatedAt: number) {
  useEventTotalStore.setState(state => {
    if (state.updatedAt <= updatedAt) {
      return { total, donationCount, updatedAt };
    } else {
      return {};
    }
  });
}
