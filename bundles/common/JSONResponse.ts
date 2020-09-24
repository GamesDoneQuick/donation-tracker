export async function JSONResponse(response: Response) {
  const jsonPromise = response.json();
  let contentType = response.headers.get('content-type');
  contentType = contentType ? contentType.split(';')[0] : 'application/octet-stream';
  if (contentType === 'application/json') {
    if (response.ok) {
      return await jsonPromise;
    } else {
      throw jsonPromise;
    }
  }
  throw await jsonPromise;
}

export async function JSONResponseWithForbidden(response: Response) {
  const jsonPromise = response.json();
  let contentType = response.headers.get('content-type');
  contentType = contentType ? contentType.split(';')[0] : 'application/octet-stream';
  if (contentType === 'application/json') {
    if (response.ok || response.status === 403) {
      return await jsonPromise;
    } else {
      throw jsonPromise;
    }
  }
  throw new Error(`Unexpected response code for \`${response.url}\`: ${response.status} ${contentType}`);
}
