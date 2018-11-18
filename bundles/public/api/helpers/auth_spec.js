import auth from './auth';

describe('auth helpers', () => {
    describe('hasPermission', () => {
        it('returns true if the user exists, is staff, and is a superuser', () => {
            expect(auth.hasPermission({staff: true, superuser: true})).toBe(true);
        });

        it('returns true if the user exists, is staff, and has the permission in their list', () => {
            expect(auth.hasPermission({staff: true, permissions: ['app.permission']}, 'app.permission')).toBe(true);
        });

        it('returns false if the user exists, is staff, but does not have the permission', () => {
            expect(auth.hasPermission({staff: true, permissions: ['app.permission']}, 'app.other_permission')).toBe(false);
        });

        it('returns false if the user exists but is not staff', () => {
            expect(auth.hasPermission({staff: false, permissions: ['app.permission']}, 'app.permission')).toBe(false);
        });

        it('returns false if the user does not exist', () => {
            expect(auth.hasPermission(null)).toBe(false);
        });
    });
});
