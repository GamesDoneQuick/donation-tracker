import React from 'react';
import { faExclamation } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

const Exclamation = (props: any) => {
  return <FontAwesomeIcon {...props} icon={faExclamation} />;
};

export default Exclamation;
