import * as React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faExclamation } from '@fortawesome/free-solid-svg-icons';

const Exclamation = (props: any) => {
  return <FontAwesomeIcon {...props} icon={faExclamation} />;
};

export default Exclamation;
