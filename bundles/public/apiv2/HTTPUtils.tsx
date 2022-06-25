import axios from 'axios';

const instance = axios.create();

export function setAPIRoot(root: string) {
  instance.defaults.baseURL = root;
}

export function setCSRFToken(token: string) {
  instance.defaults.headers.common['X-CSRFToken'] = token;
}

export function get<ResponseType>(path: string, queryParams?: Record<string, unknown>) {
  return instance.get<ResponseType>(path, { params: queryParams });
}

export function post<ResponseType>(path: string, data?: Record<string, unknown>) {
  return instance.post<ResponseType>(path, data);
}

export function put<ResponseType>(path: string, data?: Record<string, unknown>) {
  return instance.put<ResponseType>(path, data);
}

export function patch<ResponseType>(path: string, data?: Record<string, unknown>) {
  return instance.patch<ResponseType>(path, data);
}

export function del<ResponseType>(path: string) {
  return instance.delete<ResponseType>(path);
}

export default {
  setAPIRoot,
  setCSRFToken,
  get,
  post,
  put,
  patch,
  del,
};
