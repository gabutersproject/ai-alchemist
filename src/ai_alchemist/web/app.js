"use strict";

const state = {
  route: "playground",
  settings: null,
  provider: null,
  models: [],
  modelError: "",
  messages: [],
  draft: "",
  compareDraft: "",
  controller: null,
  streaming: false,
  ghost: localStorage.getItem("ai-alchemist-ghost") === "1",
  version: "",
  history: [],
  notice: "",
};

const views = {
  playground: { kicker: "Conversation", title: "Playground" },
  compare: { kicker: "Same prompt", title: "Compare" },
  models: { kicker: "Reported by the provider", title: "Models" },
  history: { kicker: "On this computer", title: "History" },
  settings: { kicker: "Provider", title: "Settings" },
};

document.getElementById("ghost-toggle").addEventListener("click", () => {
  state.ghost = !state.ghost;
  localStorage.setItem("ai-alchemist-ghost", state.ghost ? "1" : "0");
  applyGhost();
});

window.addEventListener("hashchange", () => {
  abortActive();
  render();
});

boot();

async function boot() {
  applyGhost();
  try {
    const health = await api("/api/health");
    state.version = health.version;
  } catch {
    state.version = "";
  }
  await refreshProvider();
  render();
}

function applyGhost() {
  document.documentElement.classList.toggle("ghost", state.ghost);
  const button = document.getElementById("ghost-toggle");
  button.setAttribute("aria-pressed", state.ghost ? "true" : "false");
  button.textContent = state.ghost ? "Ghost mode on" : "Ghost mode";
}

function abortActive() {
  if (state.controller) {
    state.controller.abort();
    state.controller = null;
  }
  state.streaming = false;
}

async function refreshProvider() {
  try {
    state.settings = await api("/api/settings");
    state.provider = await api("/api/provider");
  } catch (error) {
    state.provider = {
      connected: false,
      provider_name: "Ollama",
      execution: "remote",
      detail: error.message,
      model_count: null,
    };
  }
  try {
    const listed = await api("/api/models");
    state.models = listed.models;
    state.modelError = "";
    if (listed.execution) {
      state.provider = state.provider || {};
      state.provider.execution = listed.execution;
    }
  } catch (error) {
    state.models = [];
    state.modelError = error.message;
  }
}

function render() {
  captureDrafts();
  const route = (location.hash || "#playground").slice(1);
  state.route = views[route] ? route : "playground";
  if (!views[route]) {
    location.hash = "playground";
  }
  const meta = views[state.route];
  document.getElementById("view-kicker").textContent = meta.kicker;
  document.getElementById("view-title").textContent = meta.title;
  document.getElementById("provider-chip").textContent = chipText();
  document.getElementById("version").textContent = state.version ? `Version ${state.version}` : "";
  document.getElementById("active-model").textContent = activeModelText();
  document.querySelectorAll("nav a").forEach((link) => {
    link.setAttribute("aria-current", link.dataset.route === state.route ? "page" : "false");
  });
  const main = document.getElementById("main");
  main.replaceChildren();
  const builders = {
    playground: renderPlayground,
    compare: renderCompare,
    models: renderModels,
    history: renderHistory,
    settings: renderSettings,
  };
  builders[state.route](main);
}

function captureDrafts() {
  const prompt = document.getElementById("prompt");
  const compare = document.getElementById("compare-prompt");
  if (prompt) state.draft = prompt.value;
  if (compare) state.compareDraft = compare.value;
}

function chipText() {
  const probe = state.provider;
  if (!probe) return "Checking provider…";
  if (!probe.connected) return `${probe.provider_name || "Ollama"} · Unavailable`;
  const where = probe.execution === "local" ? "Local" : "Remote";
  const count = probe.model_count == null ? "" : ` · ${probe.model_count} models`;
  return `${probe.provider_name} · ${where}${count}`;
}

function activeModelText() {
  const settings = state.settings;
  if (!settings) return "Provider not loaded";
  const where = settings.execution === "local" ? "Local inference" : "Remote inference";
  const model = settings.default_model || "No default model";
  return `${settings.provider_name} · ${model} · ${where}`;
}

function renderPlayground(main) {
  main.append(providerCallout());
  if (state.notice) main.append(el("p", { class: "status-line" }, [state.notice]));
  const modelField = el("input", {
    id: "playground-model",
    list: "model-options",
    value: (state.settings && state.settings.default_model) || "",
    autocomplete: "off",
    placeholder: "Model name",
  });
  main.append(el("label", {}, ["Active model", modelField, modelOptions()]));
  const transcript = el("div", { class: "transcript" });
  if (!state.messages.length) {
    transcript.append(
      el("div", { class: "empty" }, [
        el("h2", {}, ["Start an experiment"]),
        el("p", {}, [
          "The reply comes from the model you select, through the configured Ollama host. If that host is down, this page reports the error instead of inventing an answer.",
        ]),
      ]),
    );
  }
  state.messages.forEach((message, index) => {
    transcript.append(messageNode(message, index === state.messages.length - 1));
  });
  const prompt = el("textarea", {
    id: "prompt",
    placeholder: "Ask the selected model",
  });
  prompt.value = state.draft;
  prompt.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendPlayground();
    }
  });
  const send = el("button", { type: "button", onclick: sendPlayground, disabled: state.streaming }, ["Send"]);
  const stop = el(
    "button",
    { type: "button", class: "secondary", onclick: stopGeneration, disabled: !state.streaming },
    ["Stop"],
  );
  const fresh = el("button", { type: "button", class: "secondary", onclick: newConversation }, ["New conversation"]);
  const save = el("input", { type: "checkbox", id: "save-local" });
  save.checked = Boolean(state.settings && state.settings.persist_experiments);
  save.addEventListener("change", () => updatePersistence(save.checked));
  main.append(
    transcript,
    el("div", { class: "composer" }, [
      el("label", {}, ["Prompt", prompt]),
      el("div", { class: "actions" }, [send, stop, fresh]),
    ]),
    el("label", { class: "check" }, [
      save,
      "Save experiments on this computer",
    ]),
    el("p", { class: "help" }, [
      "Off until you turn it on. Saved prompts and replies stay in a local SQLite file and are not sent to a telemetry service.",
    ]),
  );
}

function messageNode(message, live) {
  const body = el("p", live && message.pending ? { id: "live-reply" } : {}, [message.content || (message.pending ? "Waiting for Ollama…" : "")]);
  const header = el("header", {}, [
    el("span", {}, [message.role === "user" ? "You" : message.model || "Model"]),
    message.role === "assistant" && message.content && !message.pending
      ? el("button", { type: "button", class: "secondary", onclick: () => copyText(message.content) }, ["Copy"])
      : null,
  ]);
  const node = el("article", { class: `message ${message.role}` }, [header, body]);
  if (message.error) node.append(el("p", { class: "error-box" }, [message.error]));
  if (message.stopped) node.append(el("p", { class: "help" }, ["Stopped. This partial reply was not saved."]));
  if (message.warning) node.append(el("p", { class: "help" }, [message.warning]));
  return node;
}

async function sendPlayground() {
  if (state.streaming) return;
  const box = document.getElementById("prompt");
  const prompt = (box ? box.value : state.draft).trim();
  if (!state.settings) {
    state.notice = "Settings could not be loaded.";
    render();
    return;
  }
  const model = (document.getElementById("playground-model").value || "").trim();
  if (!prompt) return;
  if (!model) {
    state.notice = "Enter a model name. AI Alchemist will not choose one for you.";
    render();
    return;
  }
  if (model !== state.settings.default_model) {
    try {
      state.settings = await api("/api/settings", {
        method: "PUT",
        body: JSON.stringify({
          ollama_host: state.settings.ollama_host,
          default_model: model,
          compare_model: state.settings.compare_model,
          persist_experiments: state.settings.persist_experiments,
          max_output_tokens: state.settings.max_output_tokens,
        }),
      });
    } catch (error) {
      state.notice = error.message;
      render();
      return;
    }
  }
  state.notice = "";
  state.draft = "";
  const prior = state.messages
    .filter((message) => message.content && !message.error)
    .map((message) => ({ role: message.role, content: message.content }));
  prior.push({ role: "user", content: prompt });
  state.messages.push({ role: "user", content: prompt });
  state.messages.push({
    role: "assistant",
    content: "",
    pending: true,
    model,
    provider: state.settings.provider_name,
  });
  state.streaming = true;
  render();
  const controller = new AbortController();
  state.controller = controller;
  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        messages: prior,
        save: Boolean(state.settings.persist_experiments),
      }),
      signal: controller.signal,
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || "The request was rejected.");
    }
    await readSse(response, (event) => {
      const current = state.messages[state.messages.length - 1];
      if (event.type === "token") {
        current.content += event.text;
        const live = document.getElementById("live-reply");
        if (live) live.textContent = current.content;
      } else if (event.type === "error") {
        current.error = event.message;
        current.pending = false;
      } else if (event.type === "stopped") {
        current.stopped = true;
        current.pending = false;
      } else if (event.type === "done") {
        current.content = event.text;
        current.pending = false;
        current.warning = event.warning;
        current.model = event.model;
      }
    });
  } catch (error) {
    const current = state.messages[state.messages.length - 1];
    if (error.name === "AbortError") {
      current.stopped = true;
      current.pending = false;
    } else {
      current.error = error.message;
      current.pending = false;
    }
  } finally {
    state.streaming = false;
    state.controller = null;
    render();
  }
}

function stopGeneration() {
  abortActive();
}

function newConversation() {
  abortActive();
  state.messages = [];
  state.draft = "";
  state.notice = "";
  render();
}

function renderCompare(main) {
  main.append(providerCallout());
  const count = state.models.length;
  if (!state.provider || !state.provider.connected) {
    main.append(el("p", { class: "callout" }, ["Connect Ollama in Settings before comparison can run."]));
  } else if (count < 2) {
    main.append(
      el("p", { class: "callout" }, [
        "Comparison needs two models on the connected Ollama host. Pull another tag yourself, then refresh. AI Alchemist will not download weights. You can still type a second model name if it is already installed.",
      ]),
    );
  }
  const prompt = el("textarea", { id: "compare-prompt", placeholder: "Prompt sent to both models" });
  prompt.value = state.compareDraft;
  const leftModel = el("input", {
    id: "compare-a",
    list: "model-options",
    value: (state.settings && state.settings.default_model) || "",
    autocomplete: "off",
  });
  const rightModel = el("input", {
    id: "compare-b",
    list: "model-options",
    value: (state.settings && state.settings.compare_model) || "",
    autocomplete: "off",
  });
  main.append(
    el("p", { class: "help" }, [
      "Same prompt, two models. A difference is not a score. AI Alchemist does not rank the replies.",
    ]),
    el("div", { class: "compare-grid" }, [
      el("label", {}, ["First model", leftModel]),
      el("label", {}, ["Second model", rightModel]),
    ]),
    modelOptions(),
    el("label", {}, ["Prompt", prompt]),
    el("div", { class: "actions" }, [
      el("button", { type: "button", onclick: runCompare }, ["Compare"]),
      el("button", { type: "button", class: "secondary", onclick: () => refreshAndRender() }, ["Refresh models"]),
    ]),
    el("div", { class: "compare-grid", id: "compare-grid" }, [
      column("Left", leftModel.value),
      column("Right", rightModel.value),
    ]),
  );
}

function column(title, model) {
  return el("section", { class: "column" }, [
    el("header", {}, [el("strong", {}, [title]), el("span", {}, [model || "No model selected"])]),
    el("p", { class: "help" }, [model ? `${state.settings.provider_name} · ${executionLabel()}` : "Set this model in Settings."]),
  ]);
}

async function runCompare() {
  const prompt = document.getElementById("compare-prompt").value.trim();
  const grid = document.getElementById("compare-grid");
  const modelA = document.getElementById("compare-a").value.trim();
  const modelB = document.getElementById("compare-b").value.trim();
  if (!state.settings) {
    grid.replaceChildren(el("p", { class: "error-box" }, ["Settings could not be loaded."]));
    return;
  }
  if (modelA !== state.settings.default_model || modelB !== state.settings.compare_model) {
    try {
      state.settings = await api("/api/settings", {
        method: "PUT",
        body: JSON.stringify({
          ollama_host: state.settings.ollama_host,
          default_model: modelA,
          compare_model: modelB,
          persist_experiments: state.settings.persist_experiments,
          max_output_tokens: state.settings.max_output_tokens,
        }),
      });
    } catch (error) {
      grid.replaceChildren(el("p", { class: "error-box" }, [error.message]));
      return;
    }
  }
  if (!prompt || !modelA || !modelB) {
    grid.replaceChildren(
      el("p", { class: "error-box" }, ["Enter a prompt and choose two models in Settings."]),
    );
    return;
  }
  grid.replaceChildren(
    el("section", { class: "column" }, [el("p", {}, ["Waiting for this model…"])]),
    el("section", { class: "column" }, [el("p", {}, ["Waiting for this model…"])]),
  );
  const controller = new AbortController();
  state.controller = controller;
  try {
    const response = await fetch("/api/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt,
        model_a: modelA,
        model_b: modelB,
        save: Boolean(state.settings.persist_experiments),
      }),
      signal: controller.signal,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Comparison failed.");
    grid.replaceChildren(resultColumn(data.left), resultColumn(data.right));
  } catch (error) {
    const message = error.name === "AbortError" ? "Stopped before either reply finished." : error.message;
    grid.replaceChildren(el("p", { class: "error-box" }, [message]));
  } finally {
    state.controller = null;
  }
}

function resultColumn(side) {
  const body = side.ok ? side.text : side.error;
  const node = el("section", { class: "column" }, [
    el("header", {}, [
      el("strong", {}, [side.model]),
      el("span", {}, [`${side.provider_name} · ${side.ok ? "Reply" : "Failed"}`]),
    ]),
    el("p", {}, [body]),
  ]);
  if (side.ok) {
    node.append(el("button", { type: "button", class: "secondary", onclick: () => copyText(side.text) }, ["Copy"]));
  }
  if (side.warning) node.append(el("p", { class: "help" }, [side.warning]));
  return node;
}

async function renderModels(main) {
  main.append(
    el("p", { class: "help" }, [
      "Names, sizes, and descriptions come from the Ollama /api/tags response. AI Alchemist does not add benchmark scores or a download status it did not receive.",
    ]),
    el("div", { class: "actions" }, [
      el("button", { type: "button", class: "secondary", onclick: () => refreshAndRender() }, ["Refresh"]),
    ]),
  );
  if (state.modelError) {
    main.append(el("p", { class: "error-box" }, [state.modelError]));
    return;
  }
  if (!state.models.length) {
    main.append(el("p", { class: "callout" }, ["Ollama did not report any models."]));
    return;
  }
  const grid = el("div", { class: "model-grid" });
  state.models.forEach((model) => {
    const badges = [
      el("span", { class: `badge ${model.execution === "local" ? "local" : "remote"}` }, [
        model.execution === "local" ? "Local host" : "Remote host",
      ]),
      el("span", { class: "badge" }, [model.available ? "Listed by Ollama" : "Not listed"]),
    ];
    if (model.selected_default) badges.push(el("span", { class: "badge" }, ["Default"]));
    if (model.selected_compare) badges.push(el("span", { class: "badge" }, ["Comparison"]));
    grid.append(
      el("article", { class: "card" }, [
        el("header", {}, [el("h2", {}, [model.name]), el("span", {}, [model.provider_name])]),
        el("p", {}, badges),
        el("p", {}, [model.description]),
        el("p", { class: "meta" }, [
          [model.size_label, model.modified_at].filter(Boolean).join(" · ") || "No size or date was returned.",
        ]),
      ]),
    );
  });
  main.append(grid);
}

async function renderHistory(main) {
  main.append(
    el("p", { class: "help" }, [
      "History is optional and stays in a SQLite file next to the laboratory settings. It is not uploaded. Each row is one prompt and one reply.",
    ]),
  );
  let payload;
  try {
    payload = await api("/api/history");
  } catch (error) {
    if (state.route === "history") main.append(el("p", { class: "error-box" }, [error.message]));
    return;
  }
  if (state.route !== "history") return;
  state.history = payload.experiments;
  if (!payload.persist_experiments) {
    main.append(el("p", { class: "callout" }, ["Saving is off. New experiments are not stored until you enable it in the playground or in Settings."]));
  }
  if (!state.history.length) {
    main.append(el("p", { class: "callout" }, ["No experiments are stored on this computer."]));
    return;
  }
  main.append(
    el("div", { class: "actions" }, [
      el("button", { type: "button", class: "danger", onclick: clearHistory }, ["Delete all"]),
    ]),
  );
  const list = el("div", { class: "history-list" });
  state.history.forEach((item) => {
    list.append(
      el("article", { class: "history-item" }, [
        el("header", {}, [
          el("strong", {}, [item.title]),
          el("span", {}, [new Date(item.created_at).toLocaleString()]),
        ]),
        el("p", { class: "meta" }, [`${item.provider} · ${item.model} · ${item.kind}`]),
        el("p", {}, [item.prompt]),
        el("p", {}, [item.response]),
        el("button", { type: "button", class: "danger", onclick: () => removeHistory(item.id) }, ["Delete"]),
      ]),
    );
  });
  main.append(list);
}

function renderSettings(main) {
  const settings = state.settings || {
    ollama_host: "http://127.0.0.1:11434",
    default_model: "",
    compare_model: "",
    max_output_tokens: 512,
    persist_experiments: false,
    token_configured: false,
    execution: "local",
  };
  const host = el("input", { id: "host", value: settings.ollama_host, autocomplete: "off" });
  const token = el("input", {
    id: "token",
    type: "password",
    autocomplete: "new-password",
    placeholder: settings.token_configured ? "A token is saved. Leave blank to keep it." : "Optional bearer token",
  });
  const clear = el("input", { type: "checkbox", id: "clear-token" });
  const defaultModel = modelInput("default-model", settings.default_model);
  const compareModel = modelInput("compare-model", settings.compare_model);
  const tokens = el("input", { id: "max-tokens", type: "number", min: "16", max: "4096", value: String(settings.max_output_tokens) });
  const persist = el("input", { type: "checkbox", id: "persist" });
  persist.checked = settings.persist_experiments;
  const result = el("p", { id: "settings-result", class: "status-line" }, [
    state.notice ||
      (settings.token_configured ? "A provider token is stored on this machine and is not shown again." : ""),
  ]);
  main.append(
    el("p", { class: "help" }, [
      "Ollama is the provider in this release. Install it from https://ollama.com/download, start it with ollama serve, and pull a model yourself. A loopback host is local inference. Any other host is remote, and prompts are sent there.",
    ]),
    settings.execution === "remote"
      ? el("p", { class: "callout" }, ["The saved host is not loopback. Requests leave this machine."])
      : el("p", { class: "callout" }, ["The saved host is loopback, so inference stays on this machine when Ollama is running."]),
    el("form", { class: "form-grid", onsubmit: saveSettings }, [
      el("label", {}, ["Ollama host", host]),
      el("label", {}, ["Bearer token", token]),
      el("label", { class: "check" }, [clear, "Clear the saved token"]),
      el("label", {}, ["Default model", defaultModel]),
      el("label", {}, ["Comparison model", compareModel]),
      modelOptions(),
      el("label", {}, ["Maximum output tokens", tokens]),
      el("label", { class: "check" }, [persist, "Save experiments on this computer"]),
      el("div", { class: "actions" }, [
        el("button", { type: "submit" }, ["Save"]),
        el("button", { type: "button", class: "secondary", onclick: testConnection }, ["Test connection"]),
      ]),
      result,
    ]),
  );
}

function modelInput(id, value) {
  const input = el("input", { id, list: "model-options", value: value || "", autocomplete: "off" });
  return input;
}

function readSettingsForm() {
  const token = document.getElementById("token").value;
  const body = {
    ollama_host: document.getElementById("host").value,
    clear_token: document.getElementById("clear-token").checked,
    default_model: document.getElementById("default-model").value.trim(),
    compare_model: document.getElementById("compare-model").value.trim(),
    persist_experiments: document.getElementById("persist").checked,
    max_output_tokens: Number(document.getElementById("max-tokens").value),
  };
  if (token) body.ollama_token = token;
  return body;
}

async function saveSettings(event) {
  event.preventDefault();
  const result = document.getElementById("settings-result");
  try {
    state.settings = await api("/api/settings", {
      method: "PUT",
      body: JSON.stringify(readSettingsForm()),
    });
    document.getElementById("token").value = "";
    state.notice = "Saved. The token, if you entered one, is not displayed again.";
    await refreshProvider();
    render();
  } catch (error) {
    result.textContent = error.message;
  }
}

async function testConnection() {
  const result = document.getElementById("settings-result");
  try {
    const probe = await api("/api/settings/test", {
      method: "POST",
      body: JSON.stringify(readSettingsForm()),
    });
    const where = probe.execution === "local" ? "local" : "remote";
    result.textContent = probe.connected
      ? `Connected. Inference would be ${where}. ${probe.detail}`
      : probe.detail;
  } catch (error) {
    result.textContent = error.message;
  }
}

async function updatePersistence(enabled) {
  if (!state.settings) return;
  try {
    state.settings = await api("/api/settings", {
      method: "PUT",
      body: JSON.stringify({
        ollama_host: state.settings.ollama_host,
        default_model: state.settings.default_model,
        compare_model: state.settings.compare_model,
        persist_experiments: enabled,
        max_output_tokens: state.settings.max_output_tokens,
      }),
    });
    state.notice = enabled
      ? "New experiments will be saved on this computer."
      : "New experiments will not be saved.";
  } catch (error) {
    state.notice = error.message;
  }
  render();
}

async function removeHistory(id) {
  await api(`/api/history/${id}`, { method: "DELETE" });
  render();
}

async function clearHistory() {
  await api("/api/history", { method: "DELETE" });
  render();
}

async function refreshAndRender() {
  await refreshProvider();
  render();
}

function providerCallout() {
  if (!state.provider) return el("p", { class: "callout" }, ["Checking the provider…"]);
  if (!state.provider.connected) {
    return el("p", { class: "error-box" }, [state.provider.detail || "Ollama is not reachable."]);
  }
  if (state.provider.execution !== "local") {
    return el("p", { class: "callout" }, ["This Ollama host is remote. Prompts leave this machine."]);
  }
  return el("p", { class: "callout" }, [state.provider.detail || "Ollama is connected on this machine."]);
}

function executionLabel() {
  return state.settings && state.settings.execution === "local" ? "Local" : "Remote";
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.append(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  }
}

async function readSse(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop();
    chunks.forEach((chunk) => deliverSse(chunk, onEvent));
  }
  if (buffer.trim()) deliverSse(buffer, onEvent);
}

function deliverSse(chunk, onEvent) {
  const line = chunk.split("\n").find((item) => item.startsWith("data:"));
  if (!line) return;
  onEvent(JSON.parse(line.slice(5).trim()));
}

function modelOptions() {
  const list = el("datalist", { id: "model-options" });
  state.models.forEach((model) => list.append(el("option", { value: model.name })));
  return list;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (response.status === 204) return null;
  const data = await response.json();
  if (!response.ok) {
    const detail = data && data.detail ? data.detail : "Request failed";
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }
  return data;
}

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([key, value]) => {
    if (key === "class") node.className = value;
    else if (key === "value") node.value = value == null ? "" : String(value);
    else if (key === "disabled") node.disabled = Boolean(value);
    else if (key.startsWith("on") && typeof value === "function") node.addEventListener(key.slice(2), value);
    else if (value === true) node.setAttribute(key, "");
    else if (value !== false && value != null) node.setAttribute(key, String(value));
  });
  [].concat(children).forEach((child) => {
    if (child == null || child === false) return;
    node.append(child.nodeType ? child : document.createTextNode(String(child)));
  });
  return node;
}
