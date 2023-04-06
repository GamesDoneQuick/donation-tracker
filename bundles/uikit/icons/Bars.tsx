import * as React from 'react';
import { faBars } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

const Bars = (props: any) => {
  return <FontAwesomeIcon {...props} icon={faBars} />;
};

export default Bars;
