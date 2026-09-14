const AlcogamesRender = (() => {
  function plural(n, one, few, many) {
    const m10 = n % 10, m100 = n % 100;
    if (m10 === 1 && m100 !== 11) return one;
    if (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) return few;
    return many;
  }

  // Compact range for list columns: "любое", "3+", "2", "2–4".
  function playersLabel(game) {
    const min = game.min_players;
    const max = game.max_players;
    if (min === 1 && max === null) return 'любое';
    if (max === null) return `${min}+`;
    if (min === max) return `${min}`;
    return `${min}–${max}`;
  }

  // Sentence form for meta lines: "любое число игроков", "3+ игроков", "2 игрока".
  function playersSentence(game) {
    const label = playersLabel(game);
    if (label === 'любое') return 'любое число игроков';
    const n = game.max_players === null ? 5 : game.max_players;
    return `${label} ${plural(n, 'игрок', 'игрока', 'игроков')}`;
  }

  function timeLabel(game) {
    return game.minutes ? `${game.minutes} мин` : '—';
  }

  function formatDate(iso) {
    return iso.slice(0, 10);
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str == null ? '' : String(str);
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

  // One-line teaser for the list: the LLM summary, or the first sentence of the rules.
  function summaryOf(game) {
    if (game.summary) return game.summary;
    const firstLine = game.description.split('\n').map((s) => s.trim()).find(Boolean) || '';
    return truncate(firstLine, 140).text;
  }

  function gameUrl(id) {
    return `game.html?id=${encodeURIComponent(id)}`;
  }

  function rulesParagraphs(description) {
    const parts = description.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
    return parts.length ? parts : [description];
  }

  // Shared body for the rules dialog and game.html. `liked` controls the like button state.
  function gameDetailHtml(game, liked) {
    const facts = [];
    if (game.props) facts.push(`нужно: ${escapeHtml(game.props)}`);
    if (game.source) facts.push(`источник: ${renderSourceHtml(game.source)}`);
    const tags = (game.tags || []).map((t) => `<span class="bm-tag">${escapeHtml(t)}</span>`).join('');
    return `
      <div class="detail">
        <div class="detail__meta">
          <span>${escapeHtml(playersSentence(game))}</span>
          <span>${escapeHtml(timeLabel(game))}</span>
          <span class="detail__likes">${game.likes} ${plural(game.likes, 'лайк', 'лайка', 'лайков')}</span>
          <span>${escapeHtml(formatDate(game.date_added))}</span>
        </div>
        ${game.summary ? `<p class="detail__summary">${escapeHtml(game.summary)}</p>` : ''}
        <div class="detail__rules">
          <div class="bm-label">Как играть</div>
          ${rulesParagraphs(game.description).map((p) => `<p>${escapeHtml(p)}</p>`).join('')}
        </div>
        ${facts.length ? `<div class="bm-panel bm-panel--hairline detail__props"><div class="bm-meta">${facts.join(' · ')}</div></div>` : ''}
        ${tags ? `<div class="bm-tags">${tags}</div>` : ''}
        <div class="detail__actions">
          <button type="button" class="bm-btn bm-btn--lg ${liked ? 'bm-btn--secondary' : ''} like-btn" ${liked ? 'disabled' : ''}>${liked ? '[ok] лайк учтён' : '[+] нравится'}</button>
          <button type="button" class="bm-btn bm-btn--secondary bm-btn--lg close-btn">закрыть</button>
        </div>
      </div>`;
  }

  // Wires the like button inside a rendered detail; calls onLiked(newLikes) on success.
  function bindLike(container, game, onLiked) {
    const btn = container.querySelector('.like-btn');
    if (!btn) return;
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      try {
        const result = await AlcogamesAPI.likeGame(game.id);
        game.likes = result.likes;
        btn.textContent = '[ok] лайк учтён';
        btn.classList.add('bm-btn--secondary');
        const likes = container.querySelector('.detail__likes');
        if (likes) likes.textContent = `${result.likes} ${plural(result.likes, 'лайк', 'лайка', 'лайков')}`;
        if (onLiked) onLiked(result.likes);
      } catch (e) {
        btn.disabled = false;
        alert('Не удалось поставить лайк: ' + e.message);
      }
    });
  }

  // Theme: system preference by default, the nav button overrides and persists.
  function initThemeToggle(button) {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    function current() {
      return document.documentElement.getAttribute('data-theme') || (media.matches ? 'dark' : 'light');
    }
    function apply(theme) {
      document.documentElement.setAttribute('data-theme', theme);
      button.setAttribute('aria-label', theme === 'dark' ? 'включить светлую тему' : 'включить тёмную тему');
    }
    apply(current());
    button.addEventListener('click', () => {
      const next = current() === 'dark' ? 'light' : 'dark';
      apply(next);
      try { localStorage.setItem('theme', next); } catch (e) { /* ignore */ }
    });
  }

  return {
    plural,
    playersLabel,
    playersSentence,
    timeLabel,
    formatDate,
    escapeHtml,
    renderSourceHtml,
    truncate,
    summaryOf,
    gameUrl,
    rulesParagraphs,
    gameDetailHtml,
    bindLike,
    initThemeToggle,
  };
})();
