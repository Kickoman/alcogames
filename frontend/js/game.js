(() => {
  const container = document.getElementById('game-detail');

  function getIdFromQuery() {
    return new URLSearchParams(window.location.search).get('id');
  }

  function showMessage(text) {
    container.innerHTML = `<p>${AlcogamesRender.escapeHtml(text)}</p>`;
  }

  function renderGame(game) {
    const { escapeHtml, playersLabel, formatDate, renderSourceHtml } = AlcogamesRender;
    const liked = AlcogamesAPI.getLikedIds().has(game.id);

    container.innerHTML = `
      <h1>${escapeHtml(game.name)}</h1>
      <div class="meta">
        <span class="badge">👥 ${playersLabel(game)}</span>
        <span class="badge muted">${formatDate(game.date_added)}</span>
      </div>
      <p class="description">${escapeHtml(game.description)}</p>
      ${game.source ? `<p class="source">Источник: ${renderSourceHtml(game.source)}</p>` : ''}
      <button class="like-btn" ${liked ? 'disabled' : ''}>
        👍 <span class="like-count">${game.likes}</span>
      </button>
    `;

    const likeBtn = container.querySelector('.like-btn');
    likeBtn.addEventListener('click', async () => {
      likeBtn.disabled = true;
      try {
        const result = await AlcogamesAPI.likeGame(game.id);
        likeBtn.querySelector('.like-count').textContent = result.likes;
      } catch (e) {
        likeBtn.disabled = false;
        alert('Не удалось поставить лайк: ' + e.message);
      }
    });
  }

  async function load() {
    const id = getIdFromQuery();
    if (!id) {
      showMessage('Игра не указана.');
      return;
    }
    try {
      const games = await AlcogamesAPI.getGames();
      const game = games.find((g) => g.id === id);
      if (!game) {
        showMessage('Игра не найдена — возможно, она была удалена.');
        return;
      }
      document.title = game.name + ' — Алкогольные игры для вечеринок';
      renderGame(game);
    } catch (e) {
      showMessage('Не удалось загрузить игру.');
    }
  }

  load();
})();
