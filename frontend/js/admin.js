(() => {
  const loginSection = document.getElementById('login-section');
  const adminContent = document.getElementById('admin-content');
  const tokenInput = document.getElementById('token-input');
  const loginBtn = document.getElementById('login-btn');
  const loginError = document.getElementById('login-error');
  const logoutBtn = document.getElementById('logout-btn');

  const llmInput = document.getElementById('llm-input');
  const llmParseBtn = document.getElementById('llm-parse-btn');
  const llmStatus = document.getElementById('llm-status');

  const form = document.getElementById('game-form');
  const formTitle = document.getElementById('form-title');
  const fieldName = document.getElementById('field-name');
  const fieldMin = document.getElementById('field-min');
  const fieldMax = document.getElementById('field-max');
  const fieldNoMax = document.getElementById('field-no-max');
  const fieldDescription = document.getElementById('field-description');
  const fieldSource = document.getElementById('field-source');
  const saveBtn = document.getElementById('save-btn');
  const cancelEditBtn = document.getElementById('cancel-edit-btn');
  const formStatus = document.getElementById('form-status');

  const tableBody = document.getElementById('games-table-body');

  let editingId = null;
  let allGames = [];

  function showStatus(el, message, isError) {
    el.textContent = message;
    el.classList.remove('hidden');
    el.classList.toggle('error', !!isError);
    el.classList.toggle('success', !isError);
  }

  function hideStatus(el) {
    el.classList.add('hidden');
  }

  function showLoggedIn() {
    loginSection.classList.add('hidden');
    adminContent.classList.remove('hidden');
    logoutBtn.classList.remove('hidden');
    loadGamesTable();
  }

  function showLoggedOut(message) {
    adminContent.classList.add('hidden');
    loginSection.classList.remove('hidden');
    logoutBtn.classList.add('hidden');
    if (message) {
      showStatus(loginError, message, true);
    } else {
      hideStatus(loginError);
    }
  }

  loginBtn.addEventListener('click', () => {
    const value = tokenInput.value.trim();
    if (!value) return;
    AlcogamesAPI.setAdminToken(value);
    tokenInput.value = '';
    showLoggedIn();
  });

  logoutBtn.addEventListener('click', () => {
    AlcogamesAPI.clearAdminToken();
    showLoggedOut();
  });

  fieldNoMax.addEventListener('change', () => {
    fieldMax.disabled = fieldNoMax.checked;
    if (fieldNoMax.checked) fieldMax.value = '';
  });

  llmParseBtn.addEventListener('click', async () => {
    const text = llmInput.value.trim();
    if (!text) return;
    llmParseBtn.disabled = true;
    showStatus(llmStatus, 'Обращаемся к LLM...', false);
    try {
      const parsed = await AlcogamesAPI.parseWithLLM(text);
      fieldName.value = parsed.name || '';
      fieldMin.value = parsed.min_players || 1;
      if (parsed.max_players === null || parsed.max_players === undefined) {
        fieldNoMax.checked = true;
        fieldMax.value = '';
        fieldMax.disabled = true;
      } else {
        fieldNoMax.checked = false;
        fieldMax.disabled = false;
        fieldMax.value = parsed.max_players;
      }
      fieldDescription.value = parsed.description || '';
      fieldSource.value = parsed.source || '';
      showStatus(llmStatus, 'Готово — проверьте поля формы и сохраните.', false);
    } catch (e) {
      if (e.isAuthError) {
        showLoggedOut('Сессия истекла, войдите снова.');
        return;
      }
      showStatus(llmStatus, 'Ошибка: ' + e.message, true);
    } finally {
      llmParseBtn.disabled = false;
    }
  });

  function resetForm() {
    editingId = null;
    formTitle.textContent = 'Новая игра';
    form.reset();
    fieldMin.value = 1;
    fieldMax.disabled = false;
    cancelEditBtn.classList.add('hidden');
    hideStatus(formStatus);
  }

  cancelEditBtn.addEventListener('click', resetForm);

  function fillFormForEdit(game) {
    editingId = game.id;
    formTitle.textContent = 'Редактирование: ' + game.name;
    fieldName.value = game.name;
    fieldMin.value = game.min_players;
    if (game.max_players === null) {
      fieldNoMax.checked = true;
      fieldMax.value = '';
      fieldMax.disabled = true;
    } else {
      fieldNoMax.checked = false;
      fieldMax.disabled = false;
      fieldMax.value = game.max_players;
    }
    fieldDescription.value = game.description;
    fieldSource.value = game.source || '';
    cancelEditBtn.classList.remove('hidden');
    hideStatus(formStatus);
    window.scrollTo({ top: form.offsetTop - 20, behavior: 'smooth' });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      name: fieldName.value.trim(),
      min_players: parseInt(fieldMin.value, 10),
      max_players: fieldNoMax.checked ? null : parseInt(fieldMax.value, 10),
      description: fieldDescription.value.trim(),
      source: fieldSource.value.trim() || null,
    };

    saveBtn.disabled = true;
    try {
      if (editingId) {
        await AlcogamesAPI.updateGame(editingId, payload);
        showStatus(formStatus, 'Игра обновлена.', false);
      } else {
        await AlcogamesAPI.createGame(payload);
        showStatus(formStatus, 'Игра добавлена.', false);
      }
      resetForm();
      await loadGamesTable();
    } catch (err) {
      if (err.isAuthError) {
        showLoggedOut('Сессия истекла, войдите снова.');
        return;
      }
      showStatus(formStatus, 'Ошибка: ' + err.message, true);
    } finally {
      saveBtn.disabled = false;
    }
  });

  function renderTable() {
    const { escapeHtml, playersLabel } = AlcogamesRender;
    tableBody.innerHTML = '';
    allGames.forEach((game) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${escapeHtml(game.name)}</td>
        <td>${playersLabel(game)}</td>
        <td>${game.likes}</td>
        <td class="actions">
          <button type="button" class="edit-btn secondary">Изменить</button>
          <button type="button" class="delete-btn danger">Удалить</button>
        </td>
      `;
      tr.querySelector('.edit-btn').addEventListener('click', () => fillFormForEdit(game));
      tr.querySelector('.delete-btn').addEventListener('click', () => handleDelete(game));
      tableBody.appendChild(tr);
    });
  }

  async function handleDelete(game) {
    if (!confirm(`Удалить игру "${game.name}"?`)) return;
    try {
      await AlcogamesAPI.deleteGame(game.id);
      await loadGamesTable();
    } catch (e) {
      if (e.isAuthError) {
        showLoggedOut('Сессия истекла, войдите снова.');
        return;
      }
      alert('Ошибка удаления: ' + e.message);
    }
  }

  async function loadGamesTable() {
    try {
      allGames = await AlcogamesAPI.getGames();
      renderTable();
    } catch (e) {
      /* public list endpoint, transient failure - table just stays empty */
    }
  }

  if (AlcogamesAPI.getAdminToken()) {
    showLoggedIn();
  } else {
    showLoggedOut();
  }
})();
