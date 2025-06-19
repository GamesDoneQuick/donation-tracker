import React from 'react';

import { useEventFromRoute } from '@public/apiv2/hooks';
import Title from '@public/Title';

export default function EventTitle({ children }: { children?: string }) {
  const { data: { name = '' } = {} } = useEventFromRoute();
  return <Title>{`${name}${children && name && ' \u2014 '}${children ?? ''}`}</Title>;
}
