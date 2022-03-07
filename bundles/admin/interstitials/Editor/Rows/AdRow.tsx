import React from 'react';

import { Ad } from '@common/Models';

import { RowProps } from '../Rows';

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
