import React from 'react';
import moment from 'moment-timezone';

import { Run } from '@common/Models';

import { RowProps } from '../Rows';

export interface SpeedrunRowProps extends RowProps {
  item: Run;
}

export default React.memo(function SpeedrunRow({ item }: SpeedrunRowProps) {
  const { fields } = item;
  return (
    <React.Fragment>
      <td colSpan={4}>{fields.display_name || fields.name}</td>
      <td>{fields.starttime ? moment.tz(fields.starttime, moment.tz.guess()).format('LLLL') : 'unordered'}</td>
      <td>{fields.endtime ? moment.tz(fields.endtime, moment.tz.guess()).format('LLLL') : 'unordered'}</td>
      <td>{fields.setup_time.humanize()}</td>
      <td>{fields.run_time.humanize()}</td>
    </React.Fragment>
  );
});
