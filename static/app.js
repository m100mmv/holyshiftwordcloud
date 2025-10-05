(() => {
  const defaults = window.WORDCLOUD_DEFAULTS || { stopGroups: [], palette: [], font: '', themes: {}, defaultTheme: 'muted' };

  const palettePresets = { ...(defaults.themes || {}) };
  const defaultTheme = defaults.defaultTheme || 'muted';
  if (!palettePresets[defaultTheme] && defaults.palette && defaults.palette.length) {
    palettePresets[defaultTheme] = defaults.palette;
  }
  if (!Object.keys(palettePresets).length && defaults.palette && defaults.palette.length) {
    palettePresets[defaultTheme] = defaults.palette;
  }

  const basePalette = palettePresets[defaultTheme] && palettePresets[defaultTheme].length
    ? palettePresets[defaultTheme]
    : defaults.palette || [];

  const state = {
    jsonPath: '',
    fileType: 'auto',
    paletteName: defaultTheme,
    palette: Array.from(basePalette || []),
    customPalette: '',
    lastWords: [],
    lastHtml: null,
    analysis: null,
    manualAdjustments: {},
    pendingTargets: {},
    appliedAdjustments: {},
  };

  const dom = {
    fileType: document.getElementById('file-type'),
    uploadInput: document.getElementById('json-upload'),
    uploadStatus: document.getElementById('upload-status'),
    jsonPathInput: document.getElementById('json-path'),
    jsonKeyField: document.getElementById('json-key-field'),
    jsonKeys: document.getElementById('json-keys'),
    jsonAllField: document.getElementById('json-all-field'),
    jsonAllStrings: document.getElementById('json-all-strings'),
    stopwordContainer: document.getElementById('stopword-groups'),
    extraStopwords: document.getElementById('extra-stopwords'),
    removeStopwords: document.getElementById('remove-stopwords'),
    keepShort: document.getElementById('keep-short'),
    boosts: document.getElementById('boosts'),
    maxItems: document.getElementById('max-items'),
    minFont: document.getElementById('min-font'),
    maxFont: document.getElementById('max-font'),
    curvePower: document.getElementById('curve-power'),
    curvePowerValue: document.getElementById('curve-power-value'),
    referenceWeight: document.getElementById('reference-weight'),
    detectReferences: document.getElementById('detect-references'),
    paletteSelect: document.getElementById('palette'),
    customPaletteField: document.getElementById('custom-palette-field'),
    customPaletteInput: document.getElementById('custom-palette'),
    fontSelect: document.getElementById('font-family'),
    canvasWidth: document.getElementById('canvas-width'),
    canvasHeight: document.getElementById('canvas-height'),
    title: document.getElementById('title'),
    renderButton: document.getElementById('render-btn'),
    downloadPng: document.getElementById('download-png'),
    downloadHtml: document.getElementById('download-html'),
    resetButton: document.getElementById('reset-form'),
    status: document.getElementById('status'),
    canvas: document.getElementById('cloud'),
    analyzeButton: document.getElementById('analyze-btn'),
    applyAdjustments: document.getElementById('apply-adjustments'),
    clearAdjustments: document.getElementById('clear-adjustments'),
    analysisSummary: document.getElementById('analysis-summary'),
    analysisTableBody: document.querySelector('#analysis-table tbody'),
  };

  const ctx = dom.canvas.getContext('2d');

  const setStatus = (text) => {
    dom.status.textContent = text;
  };

  const sanitizeNumber = (value) => {
    if (value === '' || value === null || value === undefined) {
      return 0;
    }
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : 0;
  };

  const buildPendingAdjustmentsPayload = () => {
    const payload = {};
    Object.entries(state.manualAdjustments).forEach(([word, value]) => {
      const numeric = sanitizeNumber(value);
      if (!word || numeric === 0) {
        return;
      }
      payload[word] = numeric;
    });
    return payload;
  };

  const buildCombinedAdjustmentsPayload = () => {
    const payload = {};
    Object.entries(state.appliedAdjustments).forEach(([word, value]) => {
      const numeric = sanitizeNumber(value);
      if (!word || numeric === 0) {
        return;
      }
      payload[word] = numeric;
    });
    Object.entries(state.manualAdjustments).forEach(([word, value]) => {
      const numeric = sanitizeNumber(value);
      if (!word || numeric === 0) {
        return;
      }
      payload[word] = (payload[word] || 0) + numeric;
    });
    return payload;
  };

  const updateAdjustmentButtons = () => {
    const hasAnalysis = Boolean(state.analysis);
    const hasAdjustments = hasAnalysis && Object.keys(state.manualAdjustments).length > 0;
    dom.applyAdjustments.disabled = !hasAnalysis || !hasAdjustments;
    dom.clearAdjustments.disabled = !hasAnalysis;
  };

  const clearManualAdjustments = () => {
    state.manualAdjustments = {};
    state.pendingTargets = {};
    state.appliedAdjustments = {};
    updateAdjustmentButtons();
    if (state.analysis) {
      requestAnalysis({ silent: true });
    }
  };

  const renderAnalysis = (analysis) => {
    state.analysis = analysis || null;
    if (!analysis) {
      dom.analysisSummary.textContent = 'No analysis yet.';
      dom.analysisTableBody.innerHTML = '';
      updateAdjustmentButtons();
      return;
    }

    dom.analysisSummary.textContent = `Tokens: ${analysis.totalTokens} | Unique: ${analysis.uniqueTokens} | References: ${analysis.referenceMatches} - edit "Target Final" to rebalance`;
    const tbody = dom.analysisTableBody;
    tbody.innerHTML = '';

    const words = Array.isArray(analysis.words) ? analysis.words : [];
    words.forEach((entry) => {
      const row = document.createElement('tr');
      const finalCount = Number(entry.finalCount ?? 0);
      const pendingTarget = state.pendingTargets[entry.text];
      const pendingDelta = sanitizeNumber(state.manualAdjustments[entry.text]);
      const appliedDelta = sanitizeNumber(entry.manualAdjustment);

      if (pendingDelta !== 0) {
        row.classList.add('analysis-row--pending');
      } else if (appliedDelta !== 0) {
        row.classList.add('analysis-row--applied');
      }

      const wordCell = document.createElement('td');
      wordCell.innerHTML = `<span class="analysis-row__word">${entry.text}</span>`;
      row.appendChild(wordCell);

      const baseCell = document.createElement('td');
      baseCell.textContent = entry.baseCount ?? 0;
      baseCell.className = 'analysis-table__num';
      row.appendChild(baseCell);

      const refCell = document.createElement('td');
      refCell.textContent = entry.referenceBonus ?? 0;
      refCell.className = 'analysis-table__num';
      row.appendChild(refCell);

      const finalCell = document.createElement('td');
      finalCell.textContent = finalCount;
      finalCell.className = 'analysis-table__num';
      row.appendChild(finalCell);

      const boostCell = document.createElement('td');
      const boostValue = entry.boostMultiplier ? Number(entry.boostMultiplier).toFixed(2) : '1.00';
      boostCell.textContent = boostValue;
      boostCell.className = 'analysis-table__num';
      row.appendChild(boostCell);

      const appliedCell = document.createElement('td');
      const formattedApplied = appliedDelta > 0 ? `+${appliedDelta}` : appliedDelta.toString();
      appliedCell.textContent = formattedApplied;
      appliedCell.className = 'analysis-table__num';
      row.appendChild(appliedCell);

      const targetCell = document.createElement('td');
      const input = document.createElement('input');
      input.type = 'number';
      input.step = '1';
      input.placeholder = String(finalCount);
      if (pendingTarget !== undefined) {
        input.value = pendingTarget;
      }
      input.className = 'analysis-adjust-input';
      input.addEventListener('input', (event) => {
        const raw = event.target.value;
        if (raw === '') {
          delete state.pendingTargets[entry.text];
          delete state.manualAdjustments[entry.text];
          event.target.classList.remove('input-error');
          row.classList.remove('analysis-row--pending');
          updateAdjustmentButtons();
          return;
        }

        const value = Number(raw);
        if (!Number.isFinite(value)) {
          event.target.classList.add('input-error');
          return;
        }
        event.target.classList.remove('input-error');
        state.pendingTargets[entry.text] = value;
        const delta = value - finalCount;
        if (delta === 0) {
          delete state.manualAdjustments[entry.text];
          row.classList.remove('analysis-row--pending');
        } else {
          state.manualAdjustments[entry.text] = delta;
          row.classList.add('analysis-row--pending');
        }
        updateAdjustmentButtons();
      });
      targetCell.appendChild(input);
      targetCell.className = 'analysis-table__num';
      row.appendChild(targetCell);

      tbody.appendChild(row);
    });

    updateAdjustmentButtons();
  };

  const parseWordList = (value) => {
    if (!value) return [];
    return value
      .split(/[\s,]+/)
      .map((item) => item.trim().toLowerCase())
      .filter(Boolean);
  };

  const parseBoosts = (value) => {
    if (!value) return {};
    const result = {};
    value.split(/\n+/).forEach((line) => {
      const entry = line.trim();
      if (!entry || !entry.includes('=')) return;
      const [phrase, factor] = entry.split('=', 2);
      if (!phrase) return;
      const key = phrase.trim().toLowerCase();
      const numeric = parseFloat(factor);
      if (Number.isFinite(numeric)) {
        result[key] = numeric;
      }
    });
    return result;
  };

  const getSelectedStopGroups = () => {
    const checked = dom.stopwordContainer.querySelectorAll('input[type="checkbox"]:checked');
    return Array.from(checked).map((input) => input.value);
  };

  const parsePaletteInput = (value) => {
    if (!value) return [];
    return value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
  };

  const applyPalette = (name) => {
    state.paletteName = name;
    if (name === 'custom') {
      state.customPalette = dom.customPaletteInput.value;
      const customColours = parsePaletteInput(state.customPalette);
      if (customColours.length) {
        state.palette = customColours;
      }
    } else {
      const preset = palettePresets[name];
      if (preset && preset.length) {
        state.palette = Array.from(preset);
      } else if (defaults.palette && defaults.palette.length) {
        state.palette = Array.from(defaults.palette);
      }
    }
    dom.customPaletteField.hidden = name !== 'custom';
  };

  const syncJsonControls = () => {
    const hide = state.fileType === 'text';
    dom.jsonKeyField.hidden = hide;
    dom.jsonAllField.hidden = hide;
  };

  const updateCurveLabel = () => {
    dom.curvePowerValue.textContent = Number(dom.curvePower.value).toFixed(2);
  };

  const ensureJsonPath = () => {
    if (state.jsonPath) return state.jsonPath;
    const value = dom.jsonPathInput.value.trim();
    if (value) {
      state.jsonPath = value;
    }
    return state.jsonPath;
  };

  const gatherPayload = () => {
    const jsonPath = ensureJsonPath();
    if (!jsonPath) {
      throw new Error('Please upload a file or enter a path.');
    }

    const width = parseInt(dom.canvasWidth.value, 10) || 1920;
    const height = parseInt(dom.canvasHeight.value, 10) || 1080;
    const jsonKeys = state.fileType === 'text' ? [] : parseWordList(dom.jsonKeys.value);
    const collectAllStrings = state.fileType === 'text' ? false : dom.jsonAllStrings.checked;

    return {
      jsonPath,
      fileType: state.fileType,
      stopwordGroups: getSelectedStopGroups(),
      extraStopwords: parseWordList(dom.extraStopwords.value),
      removeStopwords: parseWordList(dom.removeStopwords.value),
      keepShort: parseWordList(dom.keepShort.value),
      boosts: parseBoosts(dom.boosts.value),
      jsonKeys,
      collectAllJsonStrings: collectAllStrings,
      maxItems: parseInt(dom.maxItems.value, 10) || 420,
      minFont: parseInt(dom.minFont.value, 10) || 9,
      maxFont: parseInt(dom.maxFont.value, 10) || 180,
      curvePower: parseFloat(dom.curvePower.value) || 0.75,
      referenceWeight: parseInt(dom.referenceWeight.value, 10) || 4,
      detectReferences: dom.detectReferences.checked,
      palette: state.palette,
      fontFamily: dom.fontSelect.value,
      width,
      height,
      title: dom.title.value,
      heading: dom.title.value,
      returnHtml: true,
      manualAdjustments: buildCombinedAdjustmentsPayload(),
    };
  };

  const drawCloud = (placed, palette, fontFamily, width, height) => {
    ctx.clearRect(0, 0, width, height);
    ctx.textAlign = 'center';
    ctx.textBaseline = 'alphabetic';

    placed.forEach((word, index) => {
      ctx.save();
      ctx.translate(word.x + width / 2, word.y + height / 2);
      ctx.rotate((word.rotate * Math.PI) / 180);
      ctx.font = `${word.weight} ${word.size}px ${fontFamily}`;
      ctx.fillStyle = palette[index % palette.length];
      ctx.fillText(word.text, 0, 0);
      ctx.restore();
    });
  };

  const requestAnalysis = async (options = {}) => {
    const { silent = false } = options;
    let payload;
    try {
      payload = gatherPayload();
    } catch (error) {
      setStatus(error.message);
      return;
    }

    payload.analysisOnly = true;
    payload.returnHtml = false;

    if (!silent) {
      setStatus('Analyzing…');
    }
    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || `Analysis failed (${response.status})`);
      }

      const data = await response.json();
      if (!data.analysis) {
        throw new Error('No analysis returned from server.');
      }

      state.manualAdjustments = {};
      state.pendingTargets = {};
      renderAnalysis(data.analysis);
      if (!silent) {
        setStatus('Analysis ready.');
      }
    } catch (error) {
      console.error(error);
      if (!silent) {
        setStatus(error.message || 'Analysis failed.');
      }
    }
  };

  const renderWords = (words, config) => {
    const { palette, fontFamily, width, height } = config;

    dom.canvas.width = width;
    dom.canvas.height = height;

    const layout = d3.layout.cloud()
      .size([width, height])
      .words(words.map((word) => ({ ...word })))
      .padding(2)
      .rotate(() => (Math.random() < 0.96 ? 0 : Math.random() < 0.5 ? -30 : 30))
      .font(fontFamily)
      .fontWeight((word) => word.weight)
      .fontSize((word) => word.size)
      .on('end', (placed) => {
        drawCloud(placed, palette, fontFamily, width, height);
        setStatus(`Rendered • ${placed.length} items`);
        dom.downloadPng.disabled = false;
        dom.downloadHtml.disabled = !state.lastHtml;
      });

    layout.start();
  };

  const downloadPng = () => {
    const url = dom.canvas.toDataURL('image/png');
    const link = document.createElement('a');
    link.href = url;
    link.download = 'holy_shift_wordcloud.png';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const downloadHtml = () => {
    if (!state.lastHtml) return;
    const blob = new Blob([state.lastHtml], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'holy_shift_wordcloud.html';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const generateCloud = async () => {
    let payload;
    try {
      payload = gatherPayload();
    } catch (error) {
      setStatus(error.message);
      return;
    }

    const pendingPayload = buildPendingAdjustmentsPayload();

    setStatus('Requesting layout…');
    dom.downloadPng.disabled = true;
    dom.downloadHtml.disabled = true;

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || `Generation failed (${response.status})`);
      }

      const data = await response.json();
      if (!data.words) {
        throw new Error('No words returned from server.');
      }

      Object.entries(pendingPayload).forEach(([word, value]) => {
        const numeric = sanitizeNumber(value);
        if (!word || numeric === 0) {
          return;
        }
        state.appliedAdjustments[word] = (state.appliedAdjustments[word] || 0) + numeric;
      });

      state.lastWords = data.words;
      state.lastHtml = data.html || null;
      if (data.analysis) {
        state.manualAdjustments = {};
        state.pendingTargets = {};
        renderAnalysis(data.analysis);
      }

      renderWords(state.lastWords, {
        palette: payload.palette,
        fontFamily: payload.fontFamily,
        width: payload.width,
        height: payload.height,
      });
    } catch (error) {
      console.error(error);
      setStatus(error.message || 'Generation failed.');
    }
  };

  const uploadJson = async (file) => {
    const body = new FormData();
    body.append('file', file);
    setStatus('Uploading…');
    dom.uploadStatus.textContent = `Uploading ${file.name}…`;

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body,
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || 'Upload failed');
      }
      const data = await response.json();
      state.jsonPath = data.jsonPath;
      dom.jsonPathInput.value = data.jsonPath;
      dom.uploadStatus.textContent = `Uploaded: ${data.filename}`;
      setStatus('Upload complete. Ready to render.');

      if (state.fileType === 'auto') {
        const name = (file.name || '').toLowerCase();
        const guessed = file.type === 'application/json' || name.endsWith('.json') ? 'json' : 'text';
        state.fileType = guessed;
        dom.fileType.value = guessed;
        syncJsonControls();
      }
    } catch (error) {
      console.error(error);
      dom.uploadStatus.textContent = 'Upload failed.';
      setStatus(error.message || 'Upload failed.');
    }
  };

  const bindEvents = () => {
    dom.fileType.addEventListener('change', (event) => {
      state.fileType = event.target.value;
      syncJsonControls();
    });

    dom.uploadInput.addEventListener('change', (event) => {
      const [file] = event.target.files;
      if (file) {
        uploadJson(file);
      }
    });

    dom.jsonPathInput.addEventListener('input', (event) => {
      const value = event.target.value.trim();
      state.jsonPath = value;
    });

    dom.jsonPathInput.addEventListener('blur', () => {
      if (state.fileType !== 'auto') {
        return;
      }
      if (!state.jsonPath) {
        return;
      }
      const guessed = state.jsonPath.toLowerCase().endsWith('.json') ? 'json' : 'text';
      state.fileType = guessed;
      dom.fileType.value = guessed;
      syncJsonControls();
    });

    dom.paletteSelect.addEventListener('change', (event) => {
      applyPalette(event.target.value);
    });

    dom.customPaletteInput.addEventListener('input', (event) => {
      state.customPalette = event.target.value;
      if (state.paletteName === 'custom') {
        const customColours = parsePaletteInput(state.customPalette);
        if (customColours.length) {
          state.palette = customColours;
        }
      }
    });

    dom.curvePower.addEventListener('input', updateCurveLabel);

    dom.renderButton.addEventListener('click', generateCloud);
    dom.downloadPng.addEventListener('click', downloadPng);
    dom.downloadHtml.addEventListener('click', downloadHtml);
    dom.analyzeButton.addEventListener('click', requestAnalysis);
    dom.applyAdjustments.addEventListener('click', () => {
      if (!state.analysis) {
        return;
      }
      generateCloud();
    });
    dom.clearAdjustments.addEventListener('click', clearManualAdjustments);
    dom.resetButton.addEventListener('click', () => {
      window.location.reload();
    });
  };

  const init = () => {
    if (!state.palette.length && defaults.palette) {
      state.palette = Array.from(defaults.palette);
    }
    dom.downloadPng.disabled = true;
    dom.downloadHtml.disabled = true;
    setStatus('Waiting for data…');
    updateCurveLabel();
    syncJsonControls();
    dom.customPaletteField.hidden = state.paletteName !== 'custom';
    bindEvents();
    updateAdjustmentButtons();
  };

  init();
})();
