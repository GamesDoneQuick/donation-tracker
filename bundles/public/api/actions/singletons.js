import HTTPUtil from '../../util/http';

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
        HTTPUtil.get(`${API_ROOT}me`)
            .then((me) => {
                dispatch({
                    type: 'MODEL_STATUS_SUCCESS',
                    model: {
                        type: 'me',
                    }
                });
                dispatch(onLoadMe(me));
            }).catch((error) => {
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
