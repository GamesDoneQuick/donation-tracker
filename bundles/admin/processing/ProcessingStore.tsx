import * as React from 'react';
import create from 'zustand';

import { Donation } from '@public/apiv2/APITypes';

let nextId = 0;

export interface HistoryAction {
  id: number;
  label: string;
  donationId: number;
}

interface ProcessingStoreState {
  /**
   * All donations the client is currently aware of, including donations that
   * have already been processed.
   */
  donations: Record<number, Donation>;
  /**
   * List of IDs of donations that are considered "unprocessed".
   */
  unprocessed: Set<number>;
  /**
   * The partition to use when browsing donations.
   */
  partition: number;
  actionHistory: HistoryAction[];
  /**
   * The total number of partitions currently in use, used as a maximum bound for `partition`.
   */
  partitionCount: number;
  setPartition(partition: number): void;
  setPartitionCount(partitionCount: number): void;
  /**
   * Add the given set of donations to the list of known donations, inserting
   * them as appropriate into the store's state. All donations loadded this way
   * will be considered "unprocessed".
   */
  loadDonations(donations: Donation[], replace?: boolean): void;
  processDonation(donation: Donation, action: string): void;
}

const useProcessingStore = create<ProcessingStoreState>(set => ({
  donations: {},
  unprocessed: new Set(),
  actionHistory: [],
  partition: 0,
  partitionCount: 1,
  loadDonations(donations: Donation[]) {
    set(state => {
      const newDonations = { ...state.donations };
      const unprocessed = new Set(state.unprocessed);
      for (const donation of donations) {
        newDonations[donation.id] = donation;
        unprocessed.add(donation.id);
      }

      return { donations: newDonations, unprocessed };
    });
  },
  processDonation(donation: Donation, action: string) {
    set(state => {
      const unprocessed = new Set(state.unprocessed);
      unprocessed.delete(donation.id);
      return {
        donations: { ...state.donations, [donation.id]: donation },
        unprocessed,
        actionHistory: [{ id: nextId++, label: action, donationId: donation.id }, ...state.actionHistory],
      };
    });
  },
  setPartition(partition) {
    set({ partition });
  },
  setPartitionCount(partitionCount) {
    set({ partitionCount });
  },
}));

export default useProcessingStore;

export function useDonation(donationId: number) {
  const donations = useProcessingStore(state => state.donations);
  return donations[donationId];
}

export function useUnprocessedDonations() {
  const [donations, unprocessed] = useProcessingStore(state => [state.donations, state.unprocessed]);
  return React.useMemo(
    () =>
      Array.from(unprocessed)
        .map(id => donations[id])
        .sort((a, b) => a.timereceived.localeCompare(b.timereceived)),
    [donations, unprocessed],
  );
}
