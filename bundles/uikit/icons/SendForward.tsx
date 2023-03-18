import * as React from 'react';

import { faArrowCircleRight } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

const SendForward = (props: any) => {
  return <FontAwesomeIcon {...props} icon={faArrowCircleRight} />;
};

export default SendForward;
