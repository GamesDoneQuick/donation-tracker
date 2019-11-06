import * as React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSquare } from '@fortawesome/free-regular-svg-icons';

const CheckboxOpen = props => {
  return <FontAwesomeIcon {...props} icon={faSquare} />;
};

export default CheckboxOpen;
