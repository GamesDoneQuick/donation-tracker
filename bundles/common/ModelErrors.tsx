import React from 'react';
import { useSelector } from 'react-redux';

export default React.memo(function ModelErrors() {
  const status = useSelector((state: any) => state.status);
  return (
    <>
      {Object.entries(status).map(
        ([model, status]: [string, any]) => status === 'error' && <div key={model}>{model}: Error</div>,
      )}
    </>
  );
});
