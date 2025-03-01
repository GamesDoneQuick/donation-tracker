import * as React from 'react';
import { TextArea } from '@faulty/gdq-design';

import { setSearchKeywords, useSearchKeywords } from './SearchKeywordsStore';

export default function SearchKeywordsInput() {
  const searchKeywords = useSearchKeywords();

  // Keywords are stored as a split array with some additional formatting. To
  // pre-fill the input from local storage on page load, we need to un-format
  // and re-join the words back into a regular string.
  const [rawWords, setRawWords] = React.useState(() => searchKeywords.map(word => word.replace(/\\b/g, '')).join(', '));

  const handleKeywordsChange = React.useCallback((searchText: string) => {
    setRawWords(searchText);
    const words = searchText.split(',');
    setSearchKeywords(words);
  }, []);

  return (
    <TextArea
      label="Keywords"
      description="Comma-separated list of words or phrases to highlight in donations"
      rows={2}
      // Ideally this would be an uncontrolled input, but for some reason the
      // component doesn't update on every change at that point, leading to
      // lost keystrokes and poor UX. So we'll just control it for now until
      // that behavior is fixed.
      value={rawWords}
      onChange={handleKeywordsChange}
    />
  );
}
