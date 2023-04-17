import * as React from 'react';
import { faMinusCircle } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

const Deny = (props: any) => {
  return <FontAwesomeIcon {...props} icon={faMinusCircle} />;
};

export default Deny;
