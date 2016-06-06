import $ from 'jquery';

function onLoadMe(me) {
    return {
        type: 'LOAD_ME',
        me
    };
}

export function fetchMe() {
    return (dispatch) => {
        dispatch({
            type: 'MODEL_STATUS_LOADING',
            model: {
                type: 'me',
            }
        });
        $.get(`${API_ROOT}me`)
            .done((me) => {
                dispatch({
                    type: 'MODEL_STATUS_SUCCESS',
                    model: {
                        type: 'me',
                    }
                });
                dispatch(onLoadMe(me));
            })
            .fail((data) => {
                dispatch({
                    type: 'MODEL_STATUS_ERROR',
                    model: {
                        type: 'me',
                    }
                });
                dispatch(onLoadMe({})); // anonymous user
            });
    };
}

export default {
    fetchMe,
};
