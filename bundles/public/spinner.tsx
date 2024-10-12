import React from 'react';

import { useConstants } from '@common/Constants';

import './spinner.css';

function Spinner({
  children,
  imageFile = 'admin/img/search.svg',
  spinning = true,
}: {
  children?: React.ReactNode;
  imageFile?: string;
  spinning?: boolean;
}) {
  const { STATIC_URL } = useConstants();

  return spinning ? (
    <img className="tracker--spinner" data-test-id="spinner" src={STATIC_URL + imageFile} alt="loading" />
  ) : (
    <>{children}</>
  );
}

export default Spinner;
