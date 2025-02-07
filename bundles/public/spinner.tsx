import React from 'react';
import cn from 'classnames';

import './spinner.css';

function Spinner({
  children,
  element: Element = 'span',
  showPartial = false,
  spinning,
}: {
  children?: React.ReactNode;
  element?: React.ElementType<React.PropsWithChildren<{ className?: string }>>;
  showPartial?: boolean;
  spinning: boolean;
}) {
  return (
    <>
      {spinning ? (
        <span>
          <div className="fa fa-spinner tracker__spinner" data-test-id="spinner" />
          {showPartial && <Element className={cn('tracker__spinner--partial')}>{children}</Element>}
        </span>
      ) : (
        children
      )}
    </>
  );
}

export default Spinner;
