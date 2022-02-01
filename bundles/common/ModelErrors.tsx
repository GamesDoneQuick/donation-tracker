import { useSelector } from 'react-redux';
import React from 'react';

export default React.memo(function ModelErrors() {
  const status = useSelector((state: any) => state.status);
  return (
    <>
      {Object.entries(status).map(([model, status]: [string, any]) => status === 'error' && <div>{model}: Error</div>)}
    </>
  );
});
