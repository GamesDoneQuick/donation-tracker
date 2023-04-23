import { useSelector } from 'react-redux';

import { Permission } from '@common/Permissions';

// FIXME: give these actual types

export function hasPermission(user: any, permission: Permission) {
  return !!user?.staff && (user.superuser || (user.permissions || []).indexOf(permission) !== -1);
}

export function usePermission(permission: Permission) {
  const me = useSelector((state: any) => state.singletons.me);
  return hasPermission(me, permission);
}

export function usePermissions(permissions: Permission[]) {
  const me = useSelector((state: any) => state.singletons.me);
  return permissions.every(p => hasPermission(me, p));
}

export default {
  hasPermission,
};
