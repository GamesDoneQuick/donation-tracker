export async function paginatedFetch<T>(base: string, offset = 0, limit = 500): Promise<T[]> {
  const results = (await fetch(`${base}&offset=${offset}&limit=${limit}`).then(response => response.json())) as T[];

  if (results.length === limit) {
    return [...results, ...((await paginatedFetch<T>(base, offset + limit, limit)) as T[])];
  } else {
    return results;
  }
}
