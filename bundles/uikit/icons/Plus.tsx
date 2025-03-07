import React from 'react';
import { faPlus } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

const Plus = (props: any) => {
  return <FontAwesomeIcon {...props} icon={faPlus} />;
};

export default Plus;
