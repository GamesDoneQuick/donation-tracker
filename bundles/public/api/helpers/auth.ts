import { Permission } from '@common/Permissions';
import { Me } from '@public/apiv2/APITypes';
import { useMeQuery } from '@public/apiv2/reducers/trackerApi';

export function hasPermission(user: Me, permission: Permission) {
  return user.staff && (user.superuser || user.permissions.includes(permission));
}

export function usePermission(...permissions: Permission[]) {
  const { data, isSuccess } = useMeQuery();

  return isSuccess && data != null && permissions.every(p => hasPermission(data, p));
}

export function useCSRFToken() {
  return document.querySelector<HTMLInputElement>('input[name=csrfmiddlewaretoken]')?.value || '';
}
