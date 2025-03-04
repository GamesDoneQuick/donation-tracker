import { Me } from '@public/apiv2/APITypes';
import { useEventFromRoute } from '@public/apiv2/hooks';
import { Event } from '@public/apiv2/Models';
import { Permission } from '@public/apiv2/Permissions';
import { useMeQuery } from '@public/apiv2/reducers/trackerApi';

export function hasPermission(user: Me, permission: Permission) {
  return user.staff && (user.superuser || user.permissions.includes(permission));
}

export function usePermission(...permissions: Permission[]) {
  const { data, isSuccess } = useMeQuery();

  return isSuccess && data != null && permissions.every(p => hasPermission(data, p));
}

export function useLockedPermission(event_or_perm?: Event | Permission, ...permissions: Permission[]) {
  const canEditLocked = usePermission('tracker.can_edit_locked_events');
  const otherPermissions = usePermission(
    ...[...(typeof event_or_perm === 'string' ? [event_or_perm] : []), ...permissions],
  );
  let { data: event } = useEventFromRoute();
  if (typeof event_or_perm !== 'string') {
    if (event && event_or_perm && event.id !== event_or_perm.id) {
      throw new Error('got different event from route and from parameter');
    }
    event = event_or_perm;
  }
  return (canEditLocked || (!!event && !event.locked)) && otherPermissions;
}

export function useCSRFToken() {
  return document.querySelector<HTMLInputElement>('input[name=csrfmiddlewaretoken]')?.value || '';
}
