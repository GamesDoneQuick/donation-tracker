import * as React from 'react';
import ReactMarkdown from 'react-markdown';

import Anchor from './Anchor';

type MarkdownProps = {
  className?: string;
  children: string;
};

// By default, we don't want to allow arbitrary markdown elements as they
// can have uncontrolled consequences. For example, embedding lots of large
// images, arbitrary HTML, and generally unwanted styles.
//
// The types defined here effectively allow users to write paragraphs of text
// with emphasized inline elements.
const DEFAULT_ALLOWED_NODE_TYPES: ReactMarkdown.NodeType[] = [
  'text',
  'break',
  'paragraph',
  'emphasis',
  'strong',
  'list',
  'link',
  'inlineCode',
];

const DEFAULT_RENDERERS = {
  link: Anchor,
};

/**
 `Markdown` renders markdown content into a `React.ReactNode` to easily display
 rich, user-defined content. It is intended to be used _inside_ of a text
 container (e.g., `Text`, or `Header`) to inherit appropriate styling based on
 the current theme.

 This component does not explicitly define any styling for the elements it
 renders, so that consumers can freely modify it as necessary.
*/
const Markdown = (props: MarkdownProps) => {
  const { className, children } = props;

  return (
    <ReactMarkdown
      className={className}
      allowedTypes={DEFAULT_ALLOWED_NODE_TYPES}
      renderers={DEFAULT_RENDERERS}
      unwrapDisallowed>
      {children}
    </ReactMarkdown>
  );
};

export default React.memo(Markdown);
