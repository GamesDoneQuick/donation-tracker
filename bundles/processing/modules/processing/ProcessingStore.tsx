import { create } from 'zustand';
import { persist } from 'zustand/middleware';

import { Donation } from '@public/apiv2/Models';

let nextId = 0;

export interface HistoryAction {
  id: number;
  label: string;
  donationId: number;
  timestamp: number;
}

export type ProcessingMode = 'flag' | 'confirm' | 'onestep';

interface ProcessingStoreState {
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
   * The way that donations become "processed". When this value changes, the
   * processing cache is cleared and will need to be refetched from the server.
   */
  processingMode: ProcessingMode;
  setProcessingMode: (processingMode: ProcessingMode) => void;
  processDonation(donation: Donation, action: string, log?: boolean): void;
  undoAction(actionId: number): void;
}

const useProcessingStore = create<ProcessingStoreState>()(
  persist(
    set => ({
      actionHistory: [] as HistoryAction[],
      partition: 0,
      partitionCount: 1,
      processingMode: 'flag',
      processDonation(donation: Donation, action: string, log = true) {
        set(state => {
          return {
            actionHistory: log
              ? [
                  { id: nextId++, label: action, donationId: donation.id, timestamp: Date.now() },
                  ...state.actionHistory,
                ]
              : state.actionHistory,
          };
        });
      },
      undoAction(actionId: number) {
        set(state => ({ actionHistory: state.actionHistory.filter(({ id }) => id !== actionId) }));
      },
      setPartition(partition) {
        set({ partition });
      },
      setPartitionCount(partitionCount) {
        set({ partitionCount });
      },
      setProcessingMode(processingMode: ProcessingMode) {
        set(state => {
          if (processingMode === state.processingMode) return state;

          return { processingMode, actionHistory: [] };
        });
      },
    }),
    {
      name: 'processing-state',
      partialize: state => ({
        partition: state.partition,
        partitionCount: state.partitionCount,
        processingMode: state.processingMode,
      }),
    },
  ),
);

export default useProcessingStore;
