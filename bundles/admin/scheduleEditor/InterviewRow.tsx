import React from 'react';
import cn from 'classnames';

import { useConstants } from '@common/Constants';
import { usePermission } from '@public/apiv2/hooks';
import { Interview } from '@public/apiv2/Models';

import TalentLinks from './TalentLinks';

import styles from './styles.mod.css';

export default function InterviewRow({ interview }: { interview: Interview }) {
  const { ADMIN_ROOT } = useConstants();
  const canViewInterviews = usePermission('tracker.view_interview');
  return (
    <tr className={cn(styles.row, 'text-success')} data-testid={`interview-${interview.id}`}>
      <td style={{ paddingLeft: 16 }}>
        Interview{!interview.public && ' (Hidden)'}
        {interview.prerecorded && ' (Prerecorded)'}
      </td>
      <td style={{ paddingLeft: 16 }}>
        <span>
          {interview.anchor != null && <span className={cn('fa', 'fa-anchor')} />}
          <span>{interview.suborder}</span>
        </span>
      </td>
      <td>{interview.topic}</td>
      <td>
        <TalentLinks talent={interview.interviewers} />
      </td>
      <td>
        <TalentLinks talent={interview.subjects} />
      </td>
      <td colSpan={2}>{interview.length.toFormat('h:mm:ss')}</td>
      {canViewInterviews && (
        <td>
          <a href={`${ADMIN_ROOT}interview/${interview.id}/`}>
            <span className={cn('fa', 'fa-external-link')} aria-hidden={true} />
          </a>
        </td>
      )}
    </tr>
  );
}
