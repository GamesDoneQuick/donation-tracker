function root() {
  return window.API_ROOT || 'http://testserver/';
}

export default {
  get SEARCH() {
    return `${root()}search/`;
  },
};
