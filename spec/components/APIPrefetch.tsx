import React from 'react';
import ReactDOM from 'react-dom';

const Internal = React.memo(function Internal({ textContent }: { textContent: string }) {
  const content = React.useMemo(
    () => (
      <script id="API_PREFETCH" type="application/json">
        {textContent}
      </script>
    ),
    [textContent],
  );
  const existing = document.getElementById('API_PREFETCH');
  if (existing && existing.textContent !== textContent) {
    throw new Error('already a prefetch element');
  }
  if (textContent) {
    const head = document.querySelector('head');
    if (head) {
      return ReactDOM.createPortal(content, head);
    } else {
      const html = document.querySelector('html');
      if (html) {
        return ReactDOM.createPortal(<head>{content}</head>, html);
      } else {
        return <React.Fragment />;
      }
    }
  } else {
    return <React.Fragment />;
  }
});

export default function APIPrefetch({ data }: { data: any }) {
  const textContent = React.useMemo(() => JSON.stringify(data), [data]);
  return <Internal textContent={textContent} />;
}
