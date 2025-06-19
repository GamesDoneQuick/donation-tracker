import React from 'react';
import ReactDOM from 'react-dom';

export default function Title({ children }: { children?: string }) {
  if (children) {
    const title = document.querySelector('title');
    if (title) {
      return ReactDOM.createPortal(<>{children}</>, title);
    } else {
      const head = document.querySelector('head');
      if (head) {
        return ReactDOM.createPortal(<title>{children}</title>, head);
      } else {
        const html = document.querySelector('html');
        if (html) {
          return ReactDOM.createPortal(
            <head>
              <title>{children}</title>
            </head>,
            html,
          );
        } else {
          return <React.Fragment />;
        }
      }
    }
  } else {
    return <React.Fragment />;
  }
}
