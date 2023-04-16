import * as React from 'react';
import { faSquare } from '@fortawesome/free-regular-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

const CheckboxOpen = (props: any) => {
  return <FontAwesomeIcon {...props} icon={faSquare} />;
};

export default CheckboxOpen;
