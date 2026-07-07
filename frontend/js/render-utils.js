const AlcogamesRender = (() => {
  function playersLabel(game) {
    const min = game.min_players;
    const max = game.max_players;
    if (min === 1 && max === null) return 'любое количество';
    if (max === null) return `${min}+`;
    if (min === max) return `${min}`;
    return `${min}–${max}`;
  }

  function formatDate(iso) {
    const d = new Date(iso);
    return d.toLocaleDateString('ru-RU');
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function renderSourceHtml(source) {
    if (/^https?:\/\//i.test(source)) {
      const safe = escapeHtml(source);
      return `<a href="${safe}" target="_blank" rel="noopener">${safe}</a>`;
    }
    return escapeHtml(source);
  }

  // Truncates at a word boundary near maxLen, so cards don't cut a word in half.
  function truncate(text, maxLen) {
    if (text.length <= maxLen) return { text, truncated: false };
    let cut = text.slice(0, maxLen);
    const lastBreak = Math.max(cut.lastIndexOf(' '), cut.lastIndexOf('\n'));
    if (lastBreak > maxLen * 0.6) cut = cut.slice(0, lastBreak);
    return { text: cut.trim() + '…', truncated: true };
  }

  function gameUrl(id) {
    return `game.html?id=${encodeURIComponent(id)}`;
  }

  return { playersLabel, formatDate, escapeHtml, renderSourceHtml, truncate, gameUrl };
})();
