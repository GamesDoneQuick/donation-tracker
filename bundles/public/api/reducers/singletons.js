function loadMe(state = {}, action = { type: 'LOAD_ME' }) {
  return { ...state, me: action.me };
}

const singletonFunctions = {
  LOAD_ME: loadMe,
};

export default function models(state = {}, action = {}) {
  if (singletonFunctions[action.type]) {
    return singletonFunctions[action.type](state, action);
  } else {
    return state;
  }
}
