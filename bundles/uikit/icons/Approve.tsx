import React from 'react';
import { faCheckCircle } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

const Approve = (props: any) => {
  return <FontAwesomeIcon {...props} icon={faCheckCircle} />;
};

export default Approve;
