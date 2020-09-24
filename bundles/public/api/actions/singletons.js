import HTTPUtil from '../../util/http';
import Endpoints from '../../../tracker/Endpoints';

function onLoadMe(me) {
  return {
    type: 'LOAD_ME',
    me,
  };
}

export function fetchMe() {
  return dispatch => {
    dispatch({
      type: 'MODEL_STATUS_LOADING',
      model: 'me',
    });
    return HTTPUtil.get(Endpoints.ME)
      .then(me => {
        dispatch({
          type: 'MODEL_STATUS_SUCCESS',
          model: 'me',
        });
        dispatch(onLoadMe(me));
      })
      .catch(error => {
        dispatch({
          type: 'MODEL_STATUS_ERROR',
          model: 'me',
        });
        dispatch(onLoadMe({})); // anonymous user
      });
  };
}

export default {
  fetchMe,
};
