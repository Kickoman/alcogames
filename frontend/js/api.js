const AlcogamesAPI = (() => {
  async function toError(res) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body && body.detail) detail = body.detail;
    } catch (e) {
      /* ignore non-JSON error bodies */
    }
    return new Error(detail);
  }

  async function getGames() {
    const res = await fetch('api/games');
    if (!res.ok) throw await toError(res);
    return res.json();
  }

  async function likeGame(id) {
    const res = await fetch(`api/games/${encodeURIComponent(id)}/like`, { method: 'POST' });
    if (!res.ok) throw await toError(res);
    return res.json();
  }

  function getLikedIds() {
    const match = document.cookie.match(/(?:^|;\s*)liked_games=([^;]*)/);
    if (!match) return new Set();
    return new Set(decodeURIComponent(match[1]).split(',').filter(Boolean));
  }

  function getAdminToken() {
    return localStorage.getItem('admin_token');
  }

  function setAdminToken(token) {
    localStorage.setItem('admin_token', token);
  }

  function clearAdminToken() {
    localStorage.removeItem('admin_token');
  }

  async function adminFetch(path, options = {}) {
    const token = getAdminToken();
    const headers = Object.assign({}, options.headers, { 'X-Admin-Token': token || '' });
    const res = await fetch(path, Object.assign({}, options, { headers }));
    if (res.status === 401) {
      clearAdminToken();
      const err = new Error('Требуется вход администратора');
      err.isAuthError = true;
      throw err;
    }
    return res;
  }

  async function createGame(data) {
    const res = await adminFetch('api/admin/games', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw await toError(res);
    return res.json();
  }

  async function updateGame(id, data) {
    const res = await adminFetch(`api/admin/games/${encodeURIComponent(id)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw await toError(res);
    return res.json();
  }

  async function deleteGame(id) {
    const res = await adminFetch(`api/admin/games/${encodeURIComponent(id)}`, { method: 'DELETE' });
    if (!res.ok) throw await toError(res);
  }

  async function parseWithLLM(text) {
    const res = await adminFetch('api/admin/parse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw await toError(res);
    return res.json();
  }

  return {
    getGames,
    likeGame,
    getLikedIds,
    getAdminToken,
    setAdminToken,
    clearAdminToken,
    adminFetch,
    createGame,
    updateGame,
    deleteGame,
    parseWithLLM,
  };
})();
