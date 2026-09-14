(() => {
  const R = AlcogamesRender;
  const QUICK_PICKS = [2, 3, 4, 5, 6, 8, 10];

  const quickPicks = document.getElementById('quick-picks');
  const playersOther = document.getElementById('players-other');
  const sortSelect = document.getElementById('sort-select');
  const randomBtn = document.getElementById('random-btn');
  const resetBtn = document.getElementById('reset-btn');
  const terminal = document.getElementById('terminal');
  const luckyPanel = document.getElementById('lucky-panel');
  const luckyTitle = document.getElementById('lucky-title');
  const luckyMeta = document.getElementById('lucky-meta');
  const luckyOpen = document.getElementById('lucky-open');
  const luckyAgain = document.getElementById('lucky-again');
  const countLabel = document.getElementById('count-label');
  const emptyNotice = document.getElementById('empty-notice');
  const errorNotice = document.getElementById('error-notice');
  const gamesList = document.getElementById('games-list');
  const scrim = document.getElementById('dialog-scrim');
  const dialogTitle = document.getElementById('dialog-title');
  const dialogBody = document.getElementById('dialog-body');
  const dialogClose = document.getElementById('dialog-close');

  let allGames = null;
  let players = null; // number or null
  let randomId = null;
  let openId = null;

  R.initThemeToggle(document.getElementById('theme-toggle'));

  function matches(game, n) {
    if (n === null) return true;
    if (n < game.min_players) return false;
    if (game.max_players !== null && n > game.max_players) return false;
    return true;
  }

  function sortGames(list, mode) {
    const out = list.slice();
    out.sort((a, b) => {
      if (mode === 'new') return b.date_added.localeCompare(a.date_added);
      if (mode === 'old') return a.date_added.localeCompare(b.date_added);
      if (mode === 'az') return a.name.localeCompare(b.name, 'ru');
      if (mode === 'za') return b.name.localeCompare(a.name, 'ru');
      return mode === 'pop' ? b.likes - a.likes : a.likes - b.likes;
    });
    return out;
  }

  function matched() {
    if (!allGames) return [];
    return sortGames(allGames.filter((g) => matches(g, players)), sortSelect.value);
  }

  function findGame(id) {
    return (allGames || []).find((g) => g.id === id) || null;
  }

  function metaLine(game) {
    return `${R.playersSentence(game)} · ${R.timeLabel(game)} · ${game.likes} ${R.plural(game.likes, 'лайк', 'лайка', 'лайков')}`;
  }

  // --- quick picks ---
  function renderPicks() {
    quickPicks.querySelectorAll('.pick').forEach((b) => b.remove());
    QUICK_PICKS.forEach((n) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'bm-btn bm-btn--lg pick ' + (players === n ? '' : 'bm-btn--secondary');
      btn.textContent = String(n);
      btn.addEventListener('click', () => {
        players = players === n ? null : n;
        playersOther.value = '';
        randomId = null;
        render();
      });
      quickPicks.insertBefore(btn, playersOther);
    });
    if (players !== null && !QUICK_PICKS.includes(players)) playersOther.value = String(players);
  }

  playersOther.addEventListener('input', () => {
    const v = parseInt(playersOther.value, 10);
    players = Number.isFinite(v) && v > 0 ? v : null;
    randomId = null;
    render();
  });

  // --- terminal / count ---
  function renderTerminal(list) {
    const total = allGames ? allGames.length : 0;
    const cmd = `$ alcogames --players ${players || 'any'} --sort ${sortSelect.value}`;
    const out = !allGames
      ? 'загрузка…'
      : `${list.length} ${R.plural(list.length, 'совпадение', 'совпадения', 'совпадений')} из ${total}`;
    terminal.innerHTML = `<div class="bm-terminal__line bm-terminal__line--cmd">${R.escapeHtml(cmd)}</div><div class="bm-terminal__line">${R.escapeHtml(out)}</div>`;
    if (!allGames) countLabel.textContent = 'загрузка…';
    else if (players) countLabel.textContent = `${list.length} из ${total} подходят`;
    else countLabel.textContent = `${total} ${R.plural(total, 'игра', 'игры', 'игр')}`;
  }

  // --- random pick ---
  function renderLucky() {
    const game = randomId ? findGame(randomId) : null;
    luckyPanel.classList.toggle('hidden', !game);
    if (!game) return;
    luckyTitle.textContent = game.name;
    luckyMeta.textContent = metaLine(game);
  }

  function pickRandom() {
    const pool = matched();
    if (!pool.length) return;
    randomId = pool[Math.floor(Math.random() * pool.length)].id;
    renderLucky();
    luckyPanel.scrollIntoView({ block: 'nearest' });
  }

  randomBtn.addEventListener('click', pickRandom);
  luckyAgain.addEventListener('click', pickRandom);
  luckyOpen.addEventListener('click', () => { if (randomId) openGame(randomId, true); });

  // --- list ---
  function renderRow(game) {
    const row = document.createElement('div');
    row.className = 'game-row';
    row.setAttribute('role', 'button');
    row.tabIndex = 0;
    row.innerHTML = `
      <div class="game-row__main">
        <div class="game-row__head">
          <span class="game-row__caret" aria-hidden="true">&gt;</span>
          <h3>${R.escapeHtml(game.name)}</h3>
        </div>
        <p class="game-row__summary">${R.escapeHtml(R.summaryOf(game))}</p>
      </div>
      <div class="game-row__stats">
        <div class="stat stat--wide"><span class="bm-label">Игроки</span><span class="stat__value">${R.escapeHtml(R.playersLabel(game))}</span></div>
        <div class="stat"><span class="bm-label">Время</span><span class="stat__value">${R.escapeHtml(R.timeLabel(game))}</span></div>
        <div class="stat"><span class="bm-label">Лайки</span><span class="stat__value like-count">${game.likes}</span></div>
      </div>`;
    row.addEventListener('click', () => openGame(game.id, true));
    row.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openGame(game.id, true); }
    });
    return row;
  }

  function render() {
    renderPicks();
    const list = matched();
    renderTerminal(list);
    renderLucky();
    gamesList.innerHTML = '';
    emptyNotice.classList.toggle('hidden', !allGames || list.length > 0);
    list.forEach((g) => gamesList.appendChild(renderRow(g)));
  }

  sortSelect.addEventListener('change', render);
  resetBtn.addEventListener('click', () => {
    players = null;
    playersOther.value = '';
    sortSelect.value = 'new';
    randomId = null;
    render();
  });

  // --- dialog ---
  function openGame(id, push) {
    const game = findGame(id);
    if (!game) return;
    openId = id;
    dialogTitle.textContent = 'правила — ' + game.name.toLowerCase();
    dialogBody.innerHTML = R.gameDetailHtml(game, AlcogamesAPI.getLikedIds().has(game.id));
    R.bindLike(dialogBody, game, () => render());
    dialogBody.querySelector('.close-btn').addEventListener('click', closeGame);
    scrim.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    dialogBody.scrollTop = 0;
    dialogClose.focus();
    if (push) history.pushState({ game: id }, '', '?game=' + encodeURIComponent(id));
  }

  function closeGame(fromHistory) {
    if (!openId) return;
    openId = null;
    scrim.classList.add('hidden');
    document.body.style.overflow = '';
    if (!fromHistory && new URLSearchParams(location.search).has('game')) history.back();
  }

  dialogClose.addEventListener('click', () => closeGame(false));
  scrim.addEventListener('click', (e) => { if (e.target === scrim) closeGame(false); });
  window.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeGame(false); });
  window.addEventListener('popstate', () => {
    const id = new URLSearchParams(location.search).get('game');
    if (id) openGame(id, false);
    else closeGame(true);
  });

  // --- load ---
  async function load() {
    try {
      allGames = await AlcogamesAPI.getGames();
      render();
      const id = new URLSearchParams(location.search).get('game');
      if (id) openGame(id, false);
    } catch (e) {
      allGames = [];
      errorNotice.classList.remove('hidden');
      render();
    }
  }

  render();
  load();
})();
