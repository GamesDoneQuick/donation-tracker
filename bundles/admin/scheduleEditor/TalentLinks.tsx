import React from 'react';

import { useConstants } from '@common/Constants';
import { usePermission } from '@public/apiv2/helpers/auth';
import { Talent } from '@public/apiv2/Models';
import { forceArray, MaybeArray } from '@public/util/Types';

export default function TalentLinks({ talent }: { talent: MaybeArray<Talent> }) {
  talent = forceArray(talent);
  const { ADMIN_ROOT } = useConstants();
  const canViewTalent = usePermission('tracker.view_talent');
  return (
    <>
      {talent.map((t, i) => (
        <React.Fragment key={t.id}>
          {i > 0 && ', '}
          {canViewTalent ? <a href={`${ADMIN_ROOT}talent/${t.id}`}>{t.name}</a> : t.name}
        </React.Fragment>
      ))}
    </>
  );
}
