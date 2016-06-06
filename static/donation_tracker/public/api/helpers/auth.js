export function hasPermission(user, permission) {
    return !!user && !!user.staff && (user.superuser || (user.permissions || []).indexOf(permission) !== -1);
}

export default {
    hasPermission,
};
