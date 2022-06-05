import * as React from 'react';

import { faMoon } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

const Moon = (props: any) => {
  return <FontAwesomeIcon {...props} icon={faMoon} />;
};

export default Moon;
