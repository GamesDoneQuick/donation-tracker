import create from 'zustand';
import { persist } from 'zustand/middleware';

export type ProcessingMode = 'flag' | 'confirm' | 'onestep';

interface ProcessingStoreState {
  /**
   * The partition to use when browsing donations.
   */
  partition: number;
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
}

const useProcessingStore = create<ProcessingStoreState>()(
  persist(
    set => ({
      partition: 0,
      partitionCount: 1,
      processingMode: 'flag',
      setPartition(partition) {
        set({ partition });
      },
      setPartitionCount(partitionCount) {
        set({ partitionCount });
      },
      setProcessingMode(processingMode) {
        set(state => {
          if (processingMode === state.processingMode) return state;

          return { processingMode, unprocessed: new Set() };
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
