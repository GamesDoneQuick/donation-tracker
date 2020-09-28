import React from 'react';

function Spinner({
  children,
  imageFile = 'ajax_select/images/loading-indicator.gif',
  spinning = true,
}: {
  children: React.ReactNode;
  imageFile?: string;
  spinning?: boolean;
}) {
  return spinning ? <img src={window.STATIC_URL + imageFile} alt="loading" /> : <>{children}</>;
}

export default Spinner;
