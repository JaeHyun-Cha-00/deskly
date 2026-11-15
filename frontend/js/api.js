// the server refuses requests without this header
export const HEADERS = { "Content-Type": "application/json", "X-Assistant": "1" };

export async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: HEADERS });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `the app answered ${response.status}`);
  }
  return response;
}

export const getJson = async (path, options) => (await api(path, options)).json();
export const sendJson = (path, method, data) => getJson(path, { method, body: JSON.stringify(data) });
