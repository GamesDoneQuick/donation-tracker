function toggleDropdown(dropdown) {
    return (dispatch) => {
        dispatch({
            type: 'DROPDOWN_TOGGLE',
            dropdown
        });
    };
}

module.exports = {
    toggleDropdown,
};
