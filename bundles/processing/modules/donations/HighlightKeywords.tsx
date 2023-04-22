import * as React from 'react';
import Highlighter from 'react-highlight-words';

import { useSearchKeywords } from './SearchKeywordsStore';

import styles from './HighlightKeywords.mod.css';

interface HighlightKeywordsProps {
  children: string;
}

export default function HighlightKeywords(props: HighlightKeywordsProps) {
  const { children } = props;
  const keywords = useSearchKeywords();

  return <Highlighter highlightClassName={styles.highlighted} searchWords={keywords} textToHighlight={children} />;
}
