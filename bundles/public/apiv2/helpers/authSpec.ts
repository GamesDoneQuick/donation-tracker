import { hasPermission } from './auth';

describe('auth helpers', () => {
  describe('hasPermission', () => {
    it('returns true if the user exists, is staff, and is a superuser', () => {
      expect(
        hasPermission({ username: 'super', staff: true, superuser: true, permissions: [] }, 'tracker.view_event'),
      ).toBe(true);
    });

    it('returns true if the user exists, is staff, and has the permission in their list', () => {
      expect(
        hasPermission(
          { username: 'staff', staff: true, superuser: false, permissions: ['tracker.view_event'] },
          'tracker.view_event',
        ),
      ).toBe(true);
    });

    it('returns false if the user exists, is staff, but does not have the permission', () => {
      expect(
        hasPermission(
          { username: 'staff', staff: true, superuser: false, permissions: ['tracker.view_event'] },
          'tracker.view_ad',
        ),
      ).toBe(false);
    });

    it('returns false if the user exists and has the permission but is not staff', () => {
      expect(
        hasPermission(
          { username: 'user', staff: false, superuser: false, permissions: ['tracker.view_event'] },
          'tracker.view_event',
        ),
      ).toBe(false);
    });
  });
});
