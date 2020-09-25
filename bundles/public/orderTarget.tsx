import React from 'react';

import Spinner from './spinner';

function OrderTarget<T extends { before: boolean }, TP>({
  connectDragSource,
  nullOrder,
  spinning,
  target,
  targetProps,
  targetType: TargetType,
}: {
  connectDragSource: (children: React.ReactNode) => React.ReactElement;
  target: boolean;
  targetType: React.Component<T>;
  targetProps: TP;
  nullOrder: () => void;
  spinning: boolean;
}) {
  // @ts-expect-error TargetType is hard to figure out the type signature for
  const Target = (before: boolean) => <TargetType {...targetProps} before={before} />;
  return (
    <Spinner spinning={spinning}>
      {connectDragSource(
        <span style={{ cursor: 'move' }}>
          {target ? (
            <>
              {Target(true)}
              {Target(false)}
              {nullOrder ? (
                <span style={{ cursor: 'pointer' }} onClick={nullOrder}>
                  ❌
                </span>
              ) : null}
            </>
          ) : (
            <img alt="up" src={`${window.STATIC_URL}asc.png`} />
          )}
        </span>,
      )}
    </Spinner>
  );
}

export default OrderTarget;
