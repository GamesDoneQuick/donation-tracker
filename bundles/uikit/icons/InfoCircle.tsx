import React from 'react';
import { faInfoCircle } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

const InfoCircle = (props: any) => {
  return <FontAwesomeIcon {...props} icon={faInfoCircle} />;
};

export default InfoCircle;
