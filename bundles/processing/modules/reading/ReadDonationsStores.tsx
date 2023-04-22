import create from 'zustand';

interface ReadDonationsStoreState {
  navigation: Array<[string, string[]]>;
}

const useReadDonationsStore = create<ReadDonationsStoreState>()(() => ({
  navigation: [],
}));
