(() => {
  const R = AlcogamesRender;
  const $ = (id) => document.getElementById(id);

  const loginSection = $('login-section');
  const adminContent = $('admin-content');
  const loginForm = $('login-form');
  const tokenInput = $('token-input');
  const loginBtn = $('login-btn');
  const loginHint = $('login-hint');
  const logoutBtn = $('logout-btn');
  const adminLead = $('admin-lead');
  const globalNotice = $('global-notice');

  const gamesList = $('games-list');
  const gamesEmpty = $('games-empty');
  const newGameBtn = $('new-game-btn');

  const formPanel = $('game-form-panel');
  const form = $('game-form');
  const formTitle = $('form-title');
  const fieldName = $('field-name');
  const fieldMin = $('field-min');
  const fieldMax = $('field-max');
  const fieldNoMax = $('field-no-max');
  const fieldDescription = $('field-description');
  const fieldSummary = $('field-summary');
  const fieldMinutes = $('field-minutes');
  const fieldTags = $('field-tags');
  const fieldProps = $('field-props');
  const fieldSource = $('field-source');
  const saveBtn = $('save-btn');
  const cancelEditBtn = $('cancel-edit-btn');
  const formStatus = $('form-status');

  const llmInput = $('llm-input');
  const llmParseBtn = $('llm-parse-btn');
  const llmParseLabel = $('llm-parse-label');
  const llmProviderInfo = $('llm-provider-info');
  const llmTerminal = $('llm-terminal');
  const llmStatus = $('llm-status');
  const enrichAllBtn = $('llm-enrich-all-btn');
  const enrichStatus = $('llm-enrich-status');

  const llmSettingsForm = $('llm-settings-form');
  const llmProviderSelect = $('llm-provider');
  const llmCards = { deepseek: $('llm-card-deepseek'), yandex: $('llm-card-yandex') };
  const llmFields = {
    deepseekKey: $('llm-deepseek-key'),
    deepseekClear: $('llm-deepseek-clear'),
    deepseekBaseUrl: $('llm-deepseek-base-url'),
    deepseekModel: $('llm-deepseek-model'),
    yandexKey: $('llm-yandex-key'),
    yandexClear: $('llm-yandex-clear'),
    yandexFolder: $('llm-yandex-folder'),
    yandexModel: $('llm-yandex-model'),
  };
  const llmSaveBtn = $('llm-save-btn');
  const llmTestBtn = $('llm-test-btn');
  const llmSettingsStatus = $('llm-settings-status');

  const confirmScrim = $('confirm-scrim');
  const confirmText = $('confirm-text');
  const confirmOk = $('confirm-ok');
  const confirmCancel = $('confirm-cancel');
  const confirmClose = $('confirm-close');

  const PROVIDER_LABELS = { none: 'выключено', deepseek: 'deepseek', yandex: 'yandex cloud' };
  const LOGIN_HINT = 'значение ADMIN_TOKEN из .env';
  const GLYPHS = { ok: '[ok]', error: '[x]', info: '[i]', busy: '[..]' };

  let editingId = null;
  let allGames = [];
  let llmSettings = null;

  R.initThemeToggle($('theme-toggle'));

  // --- notices ---
  function showNotice(el, tone, title, text) {
    el.querySelector('.bm-notice__glyph').textContent = GLYPHS[tone] || GLYPHS.info;
    el.querySelector('.bm-notice__title').textContent = title || '';
    el.querySelector('.bm-notice__text').textContent = text ? (title ? ' ' : '') + text : '';
    el.classList.toggle('bm-notice--error', tone === 'error');
    el.classList.remove('hidden');
  }

  function hideNotice(el) {
    el.classList.add('hidden');
  }

  function onAuthError() {
    showLoggedOut('401 — токен не подошёл или сессия истекла, войдите снова');
  }

  // --- login ---
  function setLoginHint(text, invalid) {
    loginHint.textContent = text || LOGIN_HINT;
    loginHint.classList.toggle('is-invalid', !!invalid);
    tokenInput.classList.toggle('is-invalid', !!invalid);
  }

  function showLoggedIn(settings) {
    loginSection.classList.add('hidden');
    adminContent.classList.remove('hidden');
    hideNotice(globalNotice);
    loadGamesTable();
    if (settings) fillLLMSettingsForm(settings);
    else loadLLMSettings();
  }

  function showLoggedOut(message) {
    adminContent.classList.add('hidden');
    loginSection.classList.remove('hidden');
    setLoginHint(message, !!message);
  }

  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const value = tokenInput.value.trim();
    if (!value) {
      setLoginHint('введите токен', true);
      tokenInput.focus();
      return;
    }
    AlcogamesAPI.setAdminToken(value);
    loginBtn.disabled = true;
    try {
      const settings = await AlcogamesAPI.getLLMSettings();
      tokenInput.value = '';
      setLoginHint('', false);
      showLoggedIn(settings);
    } catch (err) {
      if (err.isAuthError) {
        setLoginHint('401 — токен не подошёл', true);
        tokenInput.focus();
      } else {
        // Server unreachable: keep the token, let the user in optimistically.
        setLoginHint('сервер недоступен: ' + err.message, true);
        showLoggedIn();
      }
    } finally {
      loginBtn.disabled = false;
    }
  });

  tokenInput.addEventListener('input', () => setLoginHint('', false));

  logoutBtn.addEventListener('click', () => {
    AlcogamesAPI.clearAdminToken();
    showLoggedOut();
  });

  // --- list ---
  function rowMeta(game) {
    const parts = [
      R.playersSentence(game),
      R.timeLabel(game),
      `${game.likes} ${R.plural(game.likes, 'лайк', 'лайка', 'лайков')}`,
      R.formatDate(game.date_added),
    ];
    if (game.tags && game.tags.length) parts.push(game.tags.join(', '));
    return parts.join(' · ');
  }

  function renderList() {
    const n = allGames.length;
    adminLead.textContent = `${n} ${R.plural(n, 'игра', 'игры', 'игр')} в каталоге. Правки пишутся в games.json сразу.`;
    gamesEmpty.classList.toggle('hidden', n > 0);
    gamesList.innerHTML = '';
    allGames.forEach((game) => {
      const row = document.createElement('div');
      row.className = 'admin-row' + (editingId === game.id ? ' is-editing' : '');
      row.innerHTML = `
        <div class="admin-row__main">
          <div class="admin-row__title">${R.escapeHtml(game.name)}</div>
          <div class="admin-row__meta">${R.escapeHtml(rowMeta(game))}</div>
        </div>
        <div class="admin-row__actions">
          <button type="button" class="bm-btn bm-btn--secondary bm-btn--sm edit-btn">править</button>
          <button type="button" class="bm-btn bm-btn--secondary bm-btn--sm enrich-btn" title="дозаполнить краткое описание, время, теги и реквизит через LLM">llm</button>
          <button type="button" class="bm-btn bm-btn--danger bm-btn--sm delete-btn" aria-label="удалить">x</button>
        </div>`;
      row.querySelector('.edit-btn').addEventListener('click', () => fillFormForEdit(game));
      row.querySelector('.delete-btn').addEventListener('click', () => handleDelete(game));
      const enrichBtn = row.querySelector('.enrich-btn');
      enrichBtn.addEventListener('click', async () => {
        enrichBtn.disabled = true;
        enrichBtn.textContent = '…';
        showNotice(enrichStatus, 'busy', 'Дозаполняем', `«${game.name}»…`);
        try {
          await enrichOne(game);
          renderList();
          showNotice(enrichStatus, 'ok', 'Дозаполнено', `«${game.name}»: готово.`);
        } catch (e) {
          enrichBtn.disabled = false;
          enrichBtn.textContent = 'llm';
          if (e.isAuthError) { onAuthError(); return; }
          showNotice(enrichStatus, 'error', 'Не дозаполнено', `«${game.name}»: ${e.message}`);
        }
      });
      gamesList.appendChild(row);
    });
  }

  async function loadGamesTable() {
    try {
      allGames = await AlcogamesAPI.getGames();
      renderList();
    } catch (e) {
      /* public list endpoint, transient failure - list just stays empty */
    }
  }

  newGameBtn.addEventListener('click', () => {
    resetForm();
    formPanel.scrollIntoView({ block: 'start', behavior: 'smooth' });
    fieldName.focus();
  });

  // --- form ---
  const formInputs = [fieldName, fieldMin, fieldMax, fieldDescription, fieldSummary, fieldMinutes, fieldTags, fieldProps, fieldSource];

  function clearInvalid() {
    formInputs.forEach((el) => el.classList.remove('is-invalid'));
  }

  function fillMeta(src) {
    fieldSummary.value = src.summary || '';
    fieldMinutes.value = src.minutes || '';
    fieldTags.value = (src.tags || []).join(', ');
    fieldProps.value = src.props || '';
  }

  function resetForm() {
    editingId = null;
    formTitle.textContent = 'Новая игра';
    form.reset();
    fieldMin.value = 1;
    fieldMax.disabled = false;
    cancelEditBtn.classList.add('hidden');
    hideNotice(formStatus);
    clearInvalid();
    renderList();
  }

  cancelEditBtn.addEventListener('click', resetForm);

  fieldNoMax.addEventListener('change', () => {
    fieldMax.disabled = fieldNoMax.checked;
    if (fieldNoMax.checked) fieldMax.value = '';
  });

  function fillFormForEdit(game) {
    editingId = game.id;
    formTitle.textContent = 'Правка игры';
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
    fillMeta(game);
    fieldSource.value = game.source || '';
    cancelEditBtn.classList.remove('hidden');
    hideNotice(formStatus);
    hideNotice(globalNotice);
    clearInvalid();
    renderList();
    formPanel.scrollIntoView({ block: 'start', behavior: 'smooth' });
  }

  function validateForm() {
    clearInvalid();
    const bad = [];
    if (!fieldName.value.trim()) bad.push(fieldName);
    if (!fieldDescription.value.trim()) bad.push(fieldDescription);
    const min = parseInt(fieldMin.value, 10);
    if (!Number.isFinite(min) || min < 1) bad.push(fieldMin);
    if (!fieldNoMax.checked) {
      const max = parseInt(fieldMax.value, 10);
      if (!Number.isFinite(max) || max < 1 || (Number.isFinite(min) && max < min)) bad.push(fieldMax);
    }
    bad.forEach((el) => el.classList.add('is-invalid'));
    return bad.length === 0;
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!validateForm()) {
      showNotice(formStatus, 'error', 'Не сохранено', 'заполните выделенные поля: название, описание и число игроков обязательны');
      return;
    }
    const payload = {
      name: fieldName.value.trim(),
      min_players: parseInt(fieldMin.value, 10),
      max_players: fieldNoMax.checked ? null : parseInt(fieldMax.value, 10),
      description: fieldDescription.value.trim(),
      summary: fieldSummary.value.trim() || null,
      minutes: fieldMinutes.value ? parseInt(fieldMinutes.value, 10) : null,
      tags: fieldTags.value.split(',').map((t) => t.trim()).filter(Boolean),
      props: fieldProps.value.trim() || null,
      source: fieldSource.value.trim() || null,
    };
    const wasEditing = !!editingId;
    saveBtn.disabled = true;
    try {
      if (wasEditing) await AlcogamesAPI.updateGame(editingId, payload);
      else await AlcogamesAPI.createGame(payload);
      resetForm();
      await loadGamesTable();
      showNotice(globalNotice, 'ok', 'Сохранено', wasEditing ? `игра «${payload.name}» обновлена.` : `игра «${payload.name}» добавлена в каталог.`);
    } catch (err) {
      if (err.isAuthError) { onAuthError(); return; }
      showNotice(formStatus, 'error', 'Не сохранено', err.message);
    } finally {
      saveBtn.disabled = false;
    }
  });

  // --- delete dialog ---
  function confirmDelete(game) {
    return new Promise((resolve) => {
      const controller = new AbortController();
      const finish = (result) => {
        controller.abort();
        confirmScrim.classList.add('hidden');
        document.body.style.overflow = '';
        resolve(result);
      };
      const opts = { signal: controller.signal };
      confirmText.textContent = `Удалить «${game.name}» из каталога? Запись исчезнет из games.json, отменить это нельзя.`;
      confirmScrim.classList.remove('hidden');
      document.body.style.overflow = 'hidden';
      confirmOk.addEventListener('click', () => finish(true), opts);
      confirmCancel.addEventListener('click', () => finish(false), opts);
      confirmClose.addEventListener('click', () => finish(false), opts);
      confirmScrim.addEventListener('click', (e) => { if (e.target === confirmScrim) finish(false); }, opts);
      window.addEventListener('keydown', (e) => { if (e.key === 'Escape') finish(false); }, opts);
      confirmCancel.focus();
    });
  }

  async function handleDelete(game) {
    if (!(await confirmDelete(game))) return;
    try {
      await AlcogamesAPI.deleteGame(game.id);
      if (editingId === game.id) resetForm();
      await loadGamesTable();
      showNotice(globalNotice, 'ok', 'Удалено', `игра «${game.name}» удалена из games.json.`);
    } catch (e) {
      if (e.isAuthError) { onAuthError(); return; }
      showNotice(globalNotice, 'error', 'Не удалено', e.message);
    }
  }

  // --- LLM parse ---
  function setTerminal(lines) {
    llmTerminal.innerHTML = lines
      .map((l, i) => `<div class="bm-terminal__line${i === 0 ? ' bm-terminal__line--cmd' : ''}">${R.escapeHtml(l)}</div>`)
      .join('');
  }

  function providerLabel(s) {
    if (!s || s.provider === 'none') return 'llm';
    return PROVIDER_LABELS[s.provider] + (s.model ? ' (' + s.model + ')' : '');
  }

  function updateParseBtn() {
    llmParseBtn.disabled = !llmInput.value.trim() || !(llmSettings && llmSettings.ready);
  }

  function renderProviderInfo() {
    const s = llmSettings;
    if (!s) llmProviderInfo.textContent = '';
    else if (s.ready) llmProviderInfo.textContent = 'провайдер: ' + providerLabel(s);
    else if (s.provider === 'none') llmProviderInfo.textContent = 'llm выключен — выберите провайдера в «настройках llm» ниже';
    else llmProviderInfo.textContent = `провайдер ${PROVIDER_LABELS[s.provider]} не настроен: нет ключа или каталога — см. «настройки llm»`;
    updateParseBtn();
  }

  llmInput.addEventListener('input', updateParseBtn);

  llmParseBtn.addEventListener('click', async () => {
    const text = llmInput.value.trim();
    if (!text) return;
    llmParseBtn.disabled = true;
    llmParseLabel.textContent = 'разбираю…';
    hideNotice(llmStatus);
    setTerminal(['$ POST /api/admin/parse', `ожидание ответа ${providerLabel(llmSettings)}…`]);
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
      fillMeta(parsed);
      fieldSource.value = parsed.source || '';
      clearInvalid();
      const filled = Object.keys(parsed).filter((k) => {
        const v = parsed[k];
        return v !== null && v !== undefined && v !== '' && !(Array.isArray(v) && v.length === 0);
      }).length;
      setTerminal(['$ POST /api/admin/parse', `200 OK · ${filled} ${R.plural(filled, 'поле', 'поля', 'полей')} распознано · ничего не сохранено`]);
      showNotice(llmStatus, 'ok', 'Поля предзаполнены', 'проверьте название, число игроков и описание в форме выше, затем нажмите «сохранить».');
    } catch (e) {
      if (e.isAuthError) { onAuthError(); return; }
      setTerminal(['$ POST /api/admin/parse', `${e.status || 'ERR'} · ${e.message}`]);
      showNotice(llmStatus, 'error', 'Не разобрано', e.message);
    } finally {
      llmParseLabel.textContent = 'распарсить через LLM';
      updateParseBtn();
    }
  });

  // --- enrich ---
  function needsMeta(game) {
    return !game.summary || !game.minutes || !(game.tags && game.tags.length);
  }

  async function enrichOne(game) {
    const updated = await AlcogamesAPI.enrichGame(game.id);
    const i = allGames.findIndex((g) => g.id === game.id);
    if (i !== -1) allGames[i] = updated;
    if (editingId === game.id) fillMeta(updated);
    return updated;
  }

  enrichAllBtn.addEventListener('click', async () => {
    const todo = allGames.filter(needsMeta);
    if (!todo.length) {
      showNotice(enrichStatus, 'info', 'Нечего дозаполнять', 'у всех игр уже есть краткое описание, время и теги.');
      return;
    }
    enrichAllBtn.disabled = true;
    let done = 0;
    const failed = [];
    for (const game of todo) {
      showNotice(enrichStatus, 'busy', 'Дозаполняем', `${done + 1} из ${todo.length}: ${game.name}…`);
      try {
        await enrichOne(game);
        done += 1;
        renderList();
      } catch (e) {
        if (e.isAuthError) {
          enrichAllBtn.disabled = false;
          onAuthError();
          return;
        }
        failed.push(`${game.name}: ${e.message}`);
      }
    }
    enrichAllBtn.disabled = false;
    if (failed.length) showNotice(enrichStatus, 'error', 'Не всё дозаполнено', `готово ${done} из ${todo.length}. не удалось — ${failed.join('; ')}`);
    else showNotice(enrichStatus, 'ok', 'Готово', `дозаполнено ${done} из ${todo.length}.`);
  });

  // --- LLM settings ---
  function keyPlaceholder(tail) {
    return tail ? 'задан, оканчивается на …' + tail : 'не задан';
  }

  function toggleProviderCards() {
    Object.keys(llmCards).forEach((name) => {
      llmCards[name].classList.toggle('hidden', llmProviderSelect.value !== name);
    });
  }

  function fillLLMSettingsForm(s) {
    llmSettings = s;
    llmProviderSelect.value = s.provider;
    llmFields.deepseekKey.value = '';
    llmFields.deepseekKey.placeholder = keyPlaceholder(s.deepseek_key_tail);
    llmFields.deepseekClear.checked = false;
    llmFields.deepseekBaseUrl.value = s.deepseek_base_url || '';
    llmFields.deepseekModel.value = s.deepseek_model || '';
    llmFields.yandexKey.value = '';
    llmFields.yandexKey.placeholder = keyPlaceholder(s.yandex_key_tail);
    llmFields.yandexClear.checked = false;
    llmFields.yandexFolder.value = s.yandex_folder_id || '';
    llmFields.yandexModel.value = s.yandex_model || '';
    toggleProviderCards();
    renderProviderInfo();
  }

  async function loadLLMSettings() {
    try {
      fillLLMSettingsForm(await AlcogamesAPI.getLLMSettings());
    } catch (e) {
      if (e.isAuthError) { onAuthError(); return; }
      llmProviderInfo.textContent = 'не удалось загрузить настройки llm: ' + e.message;
    }
  }

  llmProviderSelect.addEventListener('change', toggleProviderCards);

  llmSettingsForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      provider: llmProviderSelect.value,
      deepseek_api_key: llmFields.deepseekKey.value.trim(),
      clear_deepseek_api_key: llmFields.deepseekClear.checked,
      deepseek_base_url: llmFields.deepseekBaseUrl.value.trim(),
      deepseek_model: llmFields.deepseekModel.value.trim(),
      yandex_api_key: llmFields.yandexKey.value.trim(),
      clear_yandex_api_key: llmFields.yandexClear.checked,
      yandex_folder_id: llmFields.yandexFolder.value.trim(),
      yandex_model: llmFields.yandexModel.value.trim(),
    };
    // Empty text fields mean "leave as is", not "set to empty".
    ['deepseek_base_url', 'deepseek_model', 'yandex_model'].forEach((k) => {
      if (!payload[k]) delete payload[k];
    });
    llmSaveBtn.disabled = true;
    try {
      const s = await AlcogamesAPI.updateLLMSettings(payload);
      fillLLMSettingsForm(s);
      if (s.ready) showNotice(llmSettingsStatus, 'ok', 'Сохранено', 'активен: ' + providerLabel(s) + '.');
      else showNotice(llmSettingsStatus, 'error', 'Сохранено, но провайдер не готов', 'проверьте ключ и каталог.');
    } catch (err) {
      if (err.isAuthError) { onAuthError(); return; }
      showNotice(llmSettingsStatus, 'error', 'Не сохранено', err.message);
    } finally {
      llmSaveBtn.disabled = false;
    }
  });

  llmTestBtn.addEventListener('click', async () => {
    llmTestBtn.disabled = true;
    showNotice(llmSettingsStatus, 'busy', 'Проверяем', 'запрос к ' + providerLabel(llmSettings) + '…');
    try {
      const r = await AlcogamesAPI.testLLMSettings();
      showNotice(llmSettingsStatus, r.ok ? 'ok' : 'error', r.ok ? 'Провайдер отвечает' : 'Провайдер не отвечает', r.detail);
    } catch (err) {
      if (err.isAuthError) { onAuthError(); return; }
      showNotice(llmSettingsStatus, 'error', 'Ошибка', err.message);
    } finally {
      llmTestBtn.disabled = false;
    }
  });

  // --- boot ---
  if (AlcogamesAPI.getAdminToken()) showLoggedIn();
  else showLoggedOut();
})();
