let apiRoot: string | null = null;

export function setAPIRoot(url: string) {
  apiRoot = url;
}

export default {
  get SEARCH() {
    return `${apiRoot}search/`;
  },
  get ADD() {
    return `${apiRoot}add/`;
  },
  get EDIT() {
    return `${apiRoot}edit/`;
  },
  get COMMAND() {
    return `${apiRoot}command/`;
  },
  get ME() {
    return `${apiRoot}me/`;
  },
};
