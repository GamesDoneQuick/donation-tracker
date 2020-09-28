import React from 'react';
import cn from 'classnames';

import { Ad, Interview, ModelFields, Run } from '../../../common/Models';
import styles from './index.mod.css';
import AdRow, { AdRowProps } from './Rows/AdRow';
import SpeedrunRow, { SpeedrunRowProps } from './Rows/SpeedrunRow';
import InterviewRow, { InterviewRowProps } from './Rows/InterviewRow';

export interface RowProps {
  item: Interview | Ad | Run;
  editing: boolean;
  saveItem: ((fields: ModelFields) => void) | null;
  editItem: (() => void) | null;
  cancelEdit: (() => void) | null;
}

function Inner(props: RowProps) {
  switch (props.item.model) {
    case 'tracker.ad':
      return <AdRow {...(props as AdRowProps)} />;
    case 'tracker.interview':
      return <InterviewRow {...(props as InterviewRowProps)} />;
    case 'tracker.speedrun':
      return <SpeedrunRow {...(props as SpeedrunRowProps)} />;
  }
}

export default React.memo(function Row(props: RowProps) {
  const {
    item: { model },
  } = props;
  const shortModel = model.split('.')[1];
  return (
    <tr className={cn(styles['row'], styles[`row--${shortModel}`])}>
      <td>{shortModel}</td>
      <Inner {...props} />
    </tr>
  );
});
