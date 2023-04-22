import * as React from 'react';
import { faComment } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

const Comment = (props: any) => {
  return <FontAwesomeIcon {...props} icon={faComment} />;
};

export default Comment;
