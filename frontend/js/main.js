(() => {
  let allGames = [];
  let filterCount = null;

  const sortSelect = document.getElementById('sort-select');
  const filterInput = document.getElementById('filter-players');
  const filterBtn = document.getElementById('filter-btn');
  const filterResetBtn = document.getElementById('filter-reset-btn');
  const randomInput = document.getElementById('random-players');
  const randomBtn = document.getElementById('random-btn');
  const randomResult = document.getElementById('random-result');
  const gamesList = document.getElementById('games-list');
  const emptyState = document.getElementById('empty-state');
  const loadingState = document.getElementById('loading-state');

  function playersLabel(game) {
    const min = game.min_players;
    const max = game.max_players;
    if (min === 1 && max === null) return 'любое количество';
    if (max === null) return `${min}+`;
    if (min === max) return `${min}`;
    return `${min}–${max}`;
  }

  function matchesPlayerCount(game, count) {
    if (count === null) return true;
    if (count < game.min_players) return false;
    if (game.max_players !== null && count > game.max_players) return false;
    return true;
  }

  function sortGames(games, mode) {
    const sorted = games.slice();
    switch (mode) {
      case 'date-asc':
        sorted.sort((a, b) => a.date_added.localeCompare(b.date_added));
        break;
      case 'name-asc':
        sorted.sort((a, b) => a.name.localeCompare(b.name, 'ru'));
        break;
      case 'name-desc':
        sorted.sort((a, b) => b.name.localeCompare(a.name, 'ru'));
        break;
      case 'likes-desc':
        sorted.sort((a, b) => b.likes - a.likes);
        break;
      case 'likes-asc':
        sorted.sort((a, b) => a.likes - b.likes);
        break;
      case 'date-desc':
      default:
        sorted.sort((a, b) => b.date_added.localeCompare(a.date_added));
    }
    return sorted;
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function renderSource(source) {
    if (/^https?:\/\//i.test(source)) {
      const safe = escapeHtml(source);
      return `<a href="${safe}" target="_blank" rel="noopener">${safe}</a>`;
    }
    return escapeHtml(source);
  }

  function formatDate(iso) {
    const d = new Date(iso);
    return d.toLocaleDateString('ru-RU');
  }

  function renderCard(game, likedIds) {
    const card = document.createElement('article');
    card.className = 'game-card';
    const liked = likedIds.has(game.id);

    card.innerHTML = `
      <h2>${escapeHtml(game.name)}</h2>
      <div class="meta">
        <span class="badge">👥 ${playersLabel(game)}</span>
        <span class="badge muted">${formatDate(game.date_added)}</span>
      </div>
      <p class="description">${escapeHtml(game.description)}</p>
      ${game.source ? `<p class="source">Источник: ${renderSource(game.source)}</p>` : ''}
      <button class="like-btn" ${liked ? 'disabled' : ''}>
        👍 <span class="like-count">${game.likes}</span>
      </button>
    `;

    const likeBtn = card.querySelector('.like-btn');
    likeBtn.addEventListener('click', async () => {
      likeBtn.disabled = true;
      try {
        const result = await AlcogamesAPI.likeGame(game.id);
        likeBtn.querySelector('.like-count').textContent = result.likes;
        game.likes = result.likes;
      } catch (e) {
        likeBtn.disabled = false;
        alert('Не удалось поставить лайк: ' + e.message);
      }
    });

    return card;
  }

  function render() {
    const likedIds = AlcogamesAPI.getLikedIds();
    let games = allGames;

    if (filterCount !== null) {
      games = games.filter((g) => matchesPlayerCount(g, filterCount));
    }

    games = sortGames(games, sortSelect.value);

    gamesList.innerHTML = '';
    if (games.length === 0) {
      emptyState.textContent = 'Игр не найдено.';
      emptyState.classList.remove('hidden');
    } else {
      emptyState.classList.add('hidden');
      games.forEach((g) => gamesList.appendChild(renderCard(g, likedIds)));
    }
  }

  async function loadGames() {
    loadingState.classList.remove('hidden');
    try {
      allGames = await AlcogamesAPI.getGames();
      render();
    } catch (e) {
      gamesList.innerHTML = '';
      emptyState.textContent = 'Не удалось загрузить список игр.';
      emptyState.classList.remove('hidden');
    } finally {
      loadingState.classList.add('hidden');
    }
  }

  sortSelect.addEventListener('change', render);

  filterBtn.addEventListener('click', () => {
    const value = parseInt(filterInput.value, 10);
    filterCount = Number.isFinite(value) && value > 0 ? value : null;
    render();
  });

  filterResetBtn.addEventListener('click', () => {
    filterInput.value = '';
    filterCount = null;
    render();
  });

  randomBtn.addEventListener('click', () => {
    const value = parseInt(randomInput.value, 10);
    const count = Number.isFinite(value) && value > 0 ? value : null;
    const candidates =
      count === null ? allGames : allGames.filter((g) => matchesPlayerCount(g, count));

    randomResult.classList.remove('hidden');
    if (candidates.length === 0) {
      randomResult.innerHTML = '<p>Подходящих игр не найдено 😔</p>';
      return;
    }

    const pick = candidates[Math.floor(Math.random() * candidates.length)];
    randomResult.innerHTML = '<h3>🎲 Случайный выбор:</h3>';
    randomResult.appendChild(renderCard(pick, AlcogamesAPI.getLikedIds()));
  });

  loadGames();
})();
