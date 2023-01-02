import { useSelector } from 'react-redux';

export function hasPermission(user, permission) {
  return !!user?.staff && (user.superuser || (user.permissions || []).indexOf(permission) !== -1);
}

export function usePermission(permission) {
  const me = useSelector(state => state.singletons.me);
  return hasPermission(me, permission);
}

export function usePermissions(permissions) {
  const me = useSelector(state => state.singletons.me);
  return permissions.every(p => hasPermission(me, p));
}

export default {
  hasPermission,
};
