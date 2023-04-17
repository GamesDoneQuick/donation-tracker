import * as React from 'react';
import { faRedo } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

const Refresh = (props: any) => {
  return <FontAwesomeIcon {...props} icon={faRedo} />;
};

export default Refresh;
