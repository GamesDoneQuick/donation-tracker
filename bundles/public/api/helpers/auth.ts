import { useSelector } from 'react-redux';

import { Permission } from '@common/Permissions';
import { Me } from '@public/apiv2/APITypes';

export function hasPermission(user: Me, permission: Permission) {
  return !!user?.staff && (user.superuser || (user.permissions || []).indexOf(permission) !== -1);
}

export function usePermission(...permissions: Permission[]) {
  const me = useSelector((state: any) => state.singletons.me as Me);
  return permissions.every(p => hasPermission(me, p));
}

export default {
  hasPermission,
};
