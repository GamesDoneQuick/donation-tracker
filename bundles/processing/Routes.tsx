import { useConstants } from '@common/Constants';

export const AdminRoutes = {
  DONATION: (donationId: string | number) => `/donation/${donationId}`,
  DONOR: (donorId: string | number) => `/donor/${donorId}`,
};

export function useAdminRoute(route: string) {
  const { ADMIN_ROOT } = useConstants();
  if (ADMIN_ROOT.endsWith('/') && route.startsWith('/')) {
    route = route.slice(1);
  }

  return `${ADMIN_ROOT}${route}`;
}
