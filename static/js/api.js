/* API client: all network requests live here, making debugging and backend changes easier. */
(() => {
  const TOKEN_KEY = 'servicehub_token';
  const USER_KEY = 'servicehub_user';
  async function request(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await fetch(path, { ...options, headers });
    const result = await response.json().catch(() => ({ success: false, error: { message: 'Phản hồi máy chủ không hợp lệ.' } }));
    if (!response.ok || result.success === false) {
      const error = new Error(result?.error?.message || 'Có lỗi xảy ra.');
      error.status = response.status;
      error.code = result?.error?.code || 'UNKNOWN_ERROR';
      throw error;
    }
    return result;
  }
  window.API = {
    get: (path) => request(path),
    post: (path, data = {}) => request(path, { method: 'POST', body: JSON.stringify(data) }),
    put: (path, data = {}) => request(path, { method: 'PUT', body: JSON.stringify(data) }),
    del: (path) => request(path, { method: 'DELETE' }),
    saveSession(data) { localStorage.setItem(TOKEN_KEY, data.token); localStorage.setItem(USER_KEY, JSON.stringify(data.user)); },
    clearSession() { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY); },
    cachedUser() { try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); } catch { return null; } },
    hasToken() { return Boolean(localStorage.getItem(TOKEN_KEY)); }
  };
})();
