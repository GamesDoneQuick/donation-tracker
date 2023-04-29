import * as React from 'react';
import { FormControl, TextArea } from '@spyrothon/sparx';

import { setSearchKeywords, useSearchKeywords } from './SearchKeywordsStore';

export default function SearchKeywordsInput() {
  const searchKeywords = useSearchKeywords();

  // Keywords are stored as a split array with some additional formatting. To
  // pre-fill the input from local storage on page load, we need to un-format
  // and re-join the words back into a regular string.
  const [initialKeywords] = React.useState(() => searchKeywords.map(word => word.replace(/\\b/g, '')).join(', '));

  function handleKeywordsChange(event: React.ChangeEvent<HTMLTextAreaElement>) {
    const words = event.target.value.split(',');
    setSearchKeywords(words);
  }

  return (
    <FormControl label="Keywords" note="Comma-separated list of words or phrases to highlight in donations">
      <TextArea rows={2} defaultValue={initialKeywords} onChange={handleKeywordsChange} />
    </FormControl>
  );
}
