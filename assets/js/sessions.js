/* ==========================================================================
   SHEHARNAAMA — public walk-schedule (upcoming sessions)
   Loads published upcoming sessions, renders cards, syncs the registration
   form's session selector. All visitor-facing text is set via textContent.
   ========================================================================== */

(function () {
  "use strict";

  var config = window.SHEHARNAAMA_CONFIG || {};
  var grid = document.getElementById("sessions-grid");
  var select = document.getElementById("f-session");
  var summary = document.getElementById("session-summary");
  var modal = document.getElementById("session-modal");
  var modalBody = document.getElementById("session-modal-body");
  var modalRegister = document.getElementById("session-modal-register");

  var sessionsById = {};
  var selectedId = "";

  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function clear(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function formatDate(iso) {
    var parts = iso.split("-");
    if (parts.length !== 3) return iso;
    var month = MONTHS[parseInt(parts[1], 10) - 1] || parts[1];
    var day = String(parseInt(parts[2], 10));
    return { day: day, month: month, full: day + " " + month + " " + parts[0] };
  }

  function formatTime(hhmm) {
    var parts = hhmm.split(":");
    var h = parseInt(parts[0], 10);
    var suffix = h >= 12 ? "PM" : "AM";
    var h12 = h % 12 === 0 ? 12 : h % 12;
    return h12 + ":" + parts[1] + " " + suffix;
  }

  function formatDuration(minutes) {
    if (minutes % 60 === 0) return minutes / 60 + " hr" + (minutes === 60 ? "" : "s");
    return minutes + " min";
  }

  function capacityLabel(capacity) {
    return capacity ? "Up to " + capacity + " guests" : "Small group (proposed 8\u201312)";
  }

  function setDescription(summary, session) {
    clear(summary);
    var title = el("strong", null, session.title);
    summary.appendChild(title);
    summary.appendChild(document.createElement("br"));
    summary.appendChild(document.createTextNode(
      formatDate(session.walk_date).full + " · " + formatTime(session.start_time) +
      " · " + session.meeting_point
    ));
    summary.appendChild(document.createElement("br"));
    summary.appendChild(document.createTextNode(
      "Expressions of interest only — not a confirmed booking."
    ));
  }

  function setSelected(id, scroll) {
    selectedId = id || "";
    if (select) select.value = selectedId;
    if (summary) {
      if (selectedId && sessionsById[selectedId]) {
        setDescription(summary, sessionsById[selectedId]);
        summary.hidden = false;
      } else {
        summary.hidden = true;
      }
    }
    if (scroll) {
      var target = document.getElementById("register");
      if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function renderError() {
    clear(grid);
    var box = el("div", "sessions-error");
    box.appendChild(el("p", null, "Upcoming walks could not be loaded right now."));
    var retry = el("button", "btn btn-ghost btn-small", "Retry");
    retry.type = "button";
    retry.addEventListener("click", load);
    box.appendChild(retry);
    grid.appendChild(box);
  }

  function renderEmpty() {
    clear(grid);
    var box = el("div", "sessions-empty");
    var mark = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    mark.setAttribute("viewBox", "0 0 44 52");
    mark.setAttribute("class", "sessions-empty-mark");
    mark.setAttribute("aria-hidden", "true");
    var arch = document.createElementNS("http://www.w3.org/2000/svg", "path");
    arch.setAttribute("d", "M8 48 V22 A14 14 0 0 1 36 22 V48 M4 48 H40");
    mark.appendChild(arch);
    var path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", "M13 45 C19 40 26 44 23 37 C20 30 28 34 26 26");
    path.setAttribute("stroke-dasharray", "0.1 5");
    mark.appendChild(path);
    box.appendChild(mark);
    box.appendChild(el("p", "sessions-empty-title",
      "New walk dates are being planned. Register your interest to hear about future Sheharnaama experiences."));
    box.appendChild(el("p", "sessions-empty-note",
      "Sessions appear here once our team has verified the route, date and meeting point."));
    grid.appendChild(box);
  }

  function renderCard(session) {
    var card = el("article", "session-card");
    var when = el("div", "session-when");
    var date = formatDate(session.walk_date);
    when.appendChild(el("span", "session-day", date.day));
    when.appendChild(el("span", "session-month", date.month));
    card.appendChild(when);

    var info = el("div", "session-info");
    info.appendChild(el("p", "session-status", "Open for interest"));
    info.appendChild(el("h3", null, session.title));

    var meta = el("ul", "session-meta");
    var li1 = el("li", null, formatTime(session.start_time) + " · approx. " + formatDuration(session.duration_minutes));
    var li2 = el("li", null, "Meet at: " + session.meeting_point);
    var li3 = el("li", null, capacityLabel(session.capacity));
    meta.appendChild(li1); meta.appendChild(li2); meta.appendChild(li3);
    info.appendChild(meta);

    info.appendChild(el("p", "session-desc", session.description));

    if (session.inclusions) {
      info.appendChild(el("p", "session-inclusions", "Inclusions: " + session.inclusions));
    }
    card.appendChild(info);

    var actions = el("div", "session-actions");
    var details = el("button", "btn btn-ghost btn-small", "View details");
    details.type = "button";
    details.addEventListener("click", function () { openModal(session); });
    var register = el("button", "btn btn-primary btn-small", "Register Interest");
    register.type = "button";
    register.addEventListener("click", function () {
      setSelected(String(session.id), true);
    });
    actions.appendChild(details);
    actions.appendChild(register);
    card.appendChild(actions);

    return card;
  }

  function openModal(session) {
    clear(modalBody);

    modalBody.appendChild(el("p", "session-status", "Open for interest"));
    var title = el("h2", null, session.title);
    title.id = "session-modal-title";
    modal.setAttribute("aria-labelledby", "session-modal-title");
    modalBody.appendChild(title);

    var dl = el("dl", "session-modal-dl");
    [
      ["Date", formatDate(session.walk_date).full],
      ["Start time", formatTime(session.start_time) + " (expected duration approx. " + formatDuration(session.duration_minutes) + ")"],
      ["Meeting point", session.meeting_point],
      ["Group size", capacityLabel(session.capacity)],
      ["Inclusions", session.inclusions || "To be confirmed for this session."]
    ].forEach(function (pair) {
      dl.appendChild(el("dt", null, pair[0]));
      dl.appendChild(el("dd", null, pair[1]));
    });
    modalBody.appendChild(dl);

    modalBody.appendChild(el("p", "session-modal-note",
      "Registering interest does not automatically confirm a booking. The walk goes ahead only after the team confirms final details."));

    modalRegister.onclick = function () {
      setSelected(String(session.id), true);
      if (typeof modal.close === "function") modal.close();
    };

    if (typeof modal.showModal === "function") modal.showModal();
  }

  function populateSelect(sessions) {
    if (!select) return;
    var current = select.value;
    clear(select);
    var general = el("option", null, "General interest — no specific date");
    general.value = "";
    select.appendChild(general);
    sessions.forEach(function (session) {
      var option = el("option", null,
        session.title + " — " + formatDate(session.walk_date).full + ", " + formatTime(session.start_time));
      option.value = String(session.id);
      select.appendChild(option);
    });
    if (current && sessionsById[current]) select.value = current;
  }

  function load() {
    if (!grid) return;
    clear(grid);
    grid.appendChild(el("p", "sessions-loading", "Loading upcoming walks\u2026"));

    fetch(config.apiBase + "/api/sessions")
      .then(function (response) {
        return response.json().catch(function () { return {}; }).then(function (data) {
          return { ok: response.ok, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok) { renderError(); return; }
        var sessions = result.data && Array.isArray(result.data.items) ? result.data.items : [];
        sessionsById = {};
        sessions.forEach(function (session) { sessionsById[String(session.id)] = session; });

        if (!sessions.length) { renderEmpty(); populateSelect([]); return; }

        clear(grid);
        sessions.forEach(function (session) { grid.appendChild(renderCard(session)); });
        populateSelect(sessions);
      })
      .catch(renderError);
  }

  /* Public surface used by main.js */
  window.SheharnaamaSessions = {
    getSelectedId: function () { return selectedId ? parseInt(selectedId, 10) : null; },
    getSelected: function () { return selectedId ? sessionsById[selectedId] || null : null; },
    reload: load
  };

  if (select) {
    select.addEventListener("change", function () {
      setSelected(select.value, false);
    });
  }

  var modalCloseBtn = document.getElementById("session-modal-close");
  var modalDismissBtn = document.getElementById("session-modal-dismiss");
  function closeModal() {
    if (typeof modal.close === "function") modal.close();
  }
  if (modalCloseBtn) modalCloseBtn.addEventListener("click", closeModal);
  if (modalDismissBtn) modalDismissBtn.addEventListener("click", closeModal);
  if (modal) {
    modal.addEventListener("click", function (event) {
      if (event.target === modal && typeof modal.close === "function") modal.close();
    });
  }

  load();
})();