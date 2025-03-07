import React from 'react';
import { faCheckSquare } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

const CheckboxChecked = (props: any) => {
  return <FontAwesomeIcon {...props} icon={faCheckSquare} />;
};

export default CheckboxChecked;
