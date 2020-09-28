import React from 'react';
import { RowProps } from '../Rows.js';
import { Ad } from '../../../../common/Models';

export interface AdRowProps extends RowProps {
  item: Ad;
}

export default React.memo(function AdRow({ item: { fields } }: AdRowProps) {
  return (
    <React.Fragment>
      <td>{fields.sponsor_name}</td>
      <td>{fields.ad_name}</td>
      <td>{fields.ad_type}</td>
      <td colSpan={4}>{fields.filename}</td>
      <td>{fields.length}</td>
    </React.Fragment>
  );
});
