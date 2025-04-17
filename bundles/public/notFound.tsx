import React from 'react';
import { Text } from '@faulty/gdq-design';

import { useMeQuery } from '@public/apiv2/hooks';

export default function NotFound() {
  const { isLoading } = useMeQuery();
  return isLoading ? <div /> : <Text>That page either does not exist or you do not have permission to view it.</Text>;
}
