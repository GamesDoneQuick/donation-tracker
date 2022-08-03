import React from 'react';

import { useConstants } from '@common/Constants';

function Spinner({
  children,
  imageFile = 'ajax_select/images/loading-indicator.gif',
  spinning = true,
}: {
  children?: React.ReactNode;
  imageFile?: string;
  spinning?: boolean;
}) {
  const { STATIC_URL } = useConstants();

  return spinning ? <img data-test-id="spinner" src={STATIC_URL + imageFile} alt="loading" /> : <>{children}</>;
}

export default Spinner;
