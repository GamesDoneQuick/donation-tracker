import { useConstants } from '@common/Constants';

export const AdminRoutes = {
  DONATION: (donationId?: number) => (donationId ? `/donation/${donationId}` : ''),
  DONOR: (donorId?: number) => (donorId ? `/donor/${donorId}` : ''),
};

export function useAdminRoute(route: string) {
  const { ADMIN_ROOT } = useConstants();
  if (ADMIN_ROOT.endsWith('/') && route.startsWith('/')) {
    route = route.slice(1);
  }

  return `${ADMIN_ROOT}${route}`;
}
