import * as React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCheckSquare } from '@fortawesome/free-solid-svg-icons';

const CheckboxOpen = (props) => {
  return <FontAwesomeIcon {...props} icon={faCheckSquare} />;
};

export default CheckboxOpen;
