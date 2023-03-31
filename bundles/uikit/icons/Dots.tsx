import * as React from 'react';
import { faEllipsisH } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

const Dots = (props: any) => {
  return <FontAwesomeIcon {...props} icon={faEllipsisH} />;
};

export default Dots;
