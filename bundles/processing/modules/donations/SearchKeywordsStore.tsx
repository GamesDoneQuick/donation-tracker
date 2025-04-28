import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SearchKeywordsStoreState {
  /**
   * List of words to highlight in various searchable data and content,
   * including donation comments, donor names, logs, and more. Often used for
   * quickly noting donations from a community or friends of the runner.
   */
  keywords: string[];
}

const useSearchKeywordsStore = create<SearchKeywordsStoreState>()(
  persist(
    (): SearchKeywordsStoreState => ({
      keywords: [],
    }),
    {
      name: 'search-keywords-state',
    },
  ),
);

export default useSearchKeywordsStore;

export function useSearchKeywords() {
  return useSearchKeywordsStore(state => state.keywords);
}

export function setSearchKeywords(keywords: string[]) {
  useSearchKeywordsStore.setState({ keywords });
}
