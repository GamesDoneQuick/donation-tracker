export async function paginatedFetch<T>(
  url: string,
  params: URLSearchParams | null = null,
  offset = 0,
  limit = 500,
): Promise<T[]> {
  if (!params) {
    params = new URLSearchParams();
  }
  params.set('offset', `${offset}`);
  params.set('limit', `${limit}`);
  const results = (await fetch(`${url}?${params}`).then(response => response.json())) as T[];

  if (results.length === limit) {
    return [...results, ...((await paginatedFetch<T>(url, params, offset + limit, limit)) as T[])];
  } else {
    return results;
  }
}
