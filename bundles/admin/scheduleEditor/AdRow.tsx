import React from 'react';
import cn from 'classnames';

import { useConstants } from '@common/Constants';
import { usePermission } from '@public/apiv2/helpers/auth';
import { Ad } from '@public/apiv2/Models';

import styles from './styles.mod.css';

export default function AdRow({ ad }: { ad: Ad }) {
  const { ADMIN_ROOT } = useConstants();
  const canViewAds = usePermission('tracker.view_ad');
  return (
    <tr className={cn(styles.row, 'text-primary')}>
      <td style={{ paddingLeft: 16 }}>Ad</td>
      <td style={{ paddingLeft: 16 }}>
        <span>
          {ad.anchor != null && <span className={cn('fa', 'fa-anchor')} />}
          <span>{ad.suborder}</span>
        </span>
      </td>
      <td>{ad.ad_name}</td>
      <td>{ad.ad_type}</td>
      <td>{ad.sponsor_name}</td>
      <td colSpan={2}>{ad.length.toFormat('h:mm:ss')}</td>
      {canViewAds && (
        <td>
          <a href={`${ADMIN_ROOT}ad/${ad.id}/`}>
            <span className={cn('fa', 'fa-external-link')} aria-hidden={true} />
          </a>
        </td>
      )}
    </tr>
  );
}
