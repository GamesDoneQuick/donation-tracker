import React from 'react';
import Highlighter from 'react-highlight-words';

import { useSearchKeywords } from './SearchKeywordsStore';

import styles from './HighlightKeywords.mod.css';

/**
 * Wraps the keyword with word boundary tokens and ensures that the result is a
 * valid regex. If the keyword is not valid as a regex, it is ignored.
 */
function makeKeywordRegex(keyword: string): string | undefined {
  try {
    const regex = new RegExp(`\\b${keyword}\\b`);
    return regex.source;
  } catch (e) {
    return undefined;
  }
}

interface HighlightKeywordsProps {
  children: string;
}

export default function HighlightKeywords(props: HighlightKeywordsProps) {
  const { children } = props;
  const keywords = useSearchKeywords();

  const regexKeywords = React.useMemo(() => {
    return keywords.map(makeKeywordRegex).filter((word): word is string => word != null);
  }, [keywords]);

  return <Highlighter highlightClassName={styles.highlighted} searchWords={regexKeywords} textToHighlight={children} />;
}
