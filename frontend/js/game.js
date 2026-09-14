(() => {
  const R = AlcogamesRender;
  const container = document.getElementById('game-detail');
  const title = document.getElementById('game-title');

  R.initThemeToggle(document.getElementById('theme-toggle'));

  function showMessage(text) {
    container.innerHTML = `<p class="status-line">${R.escapeHtml(text)}</p>`;
  }

  function renderGame(game) {
    title.textContent = game.name;
    container.innerHTML = R.gameDetailHtml(game, AlcogamesAPI.getLikedIds().has(game.id));
    R.bindLike(container, game);
    container.querySelector('.close-btn').addEventListener('click', () => { window.location.href = './'; });
  }

  async function load() {
    const id = new URLSearchParams(window.location.search).get('id');
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
      document.title = game.name + ' — Алкогольные игры';
      renderGame(game);
    } catch (e) {
      showMessage('Не удалось загрузить игру.');
    }
  }

  load();
})();
