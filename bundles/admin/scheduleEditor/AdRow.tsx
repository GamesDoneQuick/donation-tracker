import React from 'react';
import cn from 'classnames';

import { useConstants } from '@common/Constants';
import { Ad } from '@public/apiv2/Models';

import styles from './styles.mod.css';

export default function AdRow({ ad }: { ad: Ad }) {
  const { ADMIN_ROOT } = useConstants();
  return (
    <tr className={cn(styles.row, 'text-primary')} data-testid={`ad-${ad.id}`}>
      <td style={{ paddingLeft: 16 }}>Ad</td>
      <td style={{ paddingLeft: 16 }}>
        <span>
          {ad.anchor != null && <span className={cn('fa', 'fa-anchor')} />}
          <span>{ad.suborder}</span>
        </span>
      </td>
      {/* padding for prize column */}
      <td />
      <td>{ad.ad_name}</td>
      <td>{ad.ad_type}</td>
      <td>{ad.sponsor_name}</td>
      <td colSpan={2}>{ad.length.toFormat('h:mm:ss')}</td>
      {/* we wouldn't see this row at all if we couldn't view ads in the admin */}
      <td>
        <a href={`${ADMIN_ROOT}ad/${ad.id}/`}>
          <span className={cn('fa', 'fa-external-link')} aria-hidden={true} />
        </a>
      </td>
    </tr>
  );
}
