/* ==========================================================================
   SHEHARNAAMA — admin console logic
   All data comes from server-authenticated endpoints; user content is
   rendered with textContent only (no innerHTML of visitor data).
   ========================================================================== */

(function () {
  "use strict";

  var loginView = document.getElementById("login-view");
  var dashboardView = document.getElementById("dashboard-view");
  var loginForm = document.getElementById("login-form");
  var loginStatus = document.getElementById("login-status");
  var loginSubmit = document.getElementById("login-submit");
  var logoutBtn = document.getElementById("admin-logout");
  var emailNotice = document.getElementById("email-notice");

  var statsEls = document.querySelectorAll("[data-stat]");
  var searchInput = document.getElementById("admin-search");
  var statusFilter = document.getElementById("admin-status-filter");
  var exportBtn = document.getElementById("admin-export");
  var tableBody = document.getElementById("admin-table-body");
  var emptyState = document.getElementById("admin-empty");
  var loadingBox = document.getElementById("admin-loading");
  var feedback = document.getElementById("admin-feedback");
  var pagePrev = document.getElementById("page-prev");
  var pageNext = document.getElementById("page-next");
  var pageIndicator = document.getElementById("page-indicator");

  var detailDialog = document.getElementById("detail-dialog");
  var detailBody = document.getElementById("detail-body");
  var detailStatus = document.getElementById("detail-status");
  var detailSave = document.getElementById("detail-save");
  var detailFeedback = document.getElementById("detail-feedback");
  var detailClose = document.getElementById("detail-close");

  var state = { page: 1, pages: 1, currentId: null };

  /* ---------- tabs ---------- */

  var tabEnquiries = document.getElementById("tab-enquiries");
  var tabSessions = document.getElementById("tab-sessions");
  var panelEnquiries = document.getElementById("enquiries-panel");
  var panelSessions = document.getElementById("sessions-panel");

  function selectTab(showSessions) {
    tabEnquiries.setAttribute("aria-selected", showSessions ? "false" : "true");
    tabSessions.setAttribute("aria-selected", showSessions ? "true" : "false");
    show(panelEnquiries, !showSessions);
    show(panelSessions, showSessions);
    if (showSessions) loadSessions();
  }
  tabEnquiries.addEventListener("click", function () { selectTab(false); });
  tabSessions.addEventListener("click", function () { selectTab(true); });

  /* ---------- helpers ---------- */

  function show(element, on) { element.hidden = !on; }

  function setStatus(target, kind, message) {
    if (!message) { target.innerHTML = ""; return; }
    var box = document.createElement("div");
    box.className = "status-box status-" + kind;
    box.textContent = message;
    target.innerHTML = "";
    target.appendChild(box);
  }

  function buildRow(label, value) {
    var dt = document.createElement("dt");
    var dd = document.createElement("dd");
    dt.textContent = label;
    dd.textContent = value === null || value === undefined || value === "" ? "\u2014" : String(value);
    return [dt, dd];
  }

  function statusLabel(status) {
    return { INTEREST_RECEIVED: "New enquiry", CONTACTED: "Contacted", WAITLISTED: "Waitlisted", CLOSED: "Closed" }[status] || status;
  }

  function experienceLabel(type) {
    return type === "private-group" ? "Private / Group Experience" : "Peth Stories Walk";
  }

  function formatDateTime(iso) {
    if (!iso) return "\u2014";
    try { return new Date(iso).toLocaleString(); } catch (e) { return iso; }
  }

  function fetchJson(url, options) {
    return fetch(url, Object.assign({ credentials: "same-origin" }, options)).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        return { ok: response.ok, status: response.status, data: data };
      });
    });
  }

  /* ---------- auth flow ---------- */

  function showLogin() {
    show(loginView, true);
    show(dashboardView, false);
    logoutBtn.hidden = true;
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  function showDashboard(noticeEmailsUnconfigured) {
    show(loginView, false);
    show(dashboardView, true);
    logoutBtn.hidden = false;
    if (typeof noticeEmailsUnconfigured === "boolean") {
      show(emailNotice, noticeEmailsUnconfigured);
    }
    refresh();
    /* Land at the top of the dashboard immediately after sign-in. */
    window.scrollTo({ top: 0, behavior: "auto" });
    var heading = document.getElementById("dash-title");
    if (heading) {
      heading.setAttribute("tabindex", "-1");
      heading.focus({ preventScroll: true });
    }
  }

  loginForm.addEventListener("submit", function (event) {
    event.preventDefault();
    var username = document.getElementById("admin-username").value;
    var password = document.getElementById("admin-password").value;
    if (!username || !password) {
      setStatus(loginStatus, "error", "Please enter both username and password.");
      return;
    }
    loginSubmit.disabled = true;
    loginSubmit.textContent = "Signing in\u2026";
    setStatus(loginStatus, "", "");

    fetchJson("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: username, password: password })
    }).then(function (result) {
      if (result.ok) {
        loginForm.reset();
        showDashboard(result.data.email_notifications === "not_configured");
      } else if (result.status === 503) {
        setStatus(loginStatus, "error", result.data.detail || "Admin access is not configured on this server.");
      } else if (result.status === 429) {
        setStatus(loginStatus, "error", result.data.detail || "Too many attempts. Please wait and try again.");
      } else {
        setStatus(loginStatus, "error", result.data.detail || "Invalid username or password.");
      }
    }).catch(function () {
      setStatus(loginStatus, "error", "Could not reach the server. Is it running?");
    }).finally(function () {
      loginSubmit.disabled = false;
      loginSubmit.textContent = "Sign in";
    });
  });

  logoutBtn.addEventListener("click", function () {
    fetchJson("/api/admin/logout", { method: "POST" }).finally(function () {
      showLogin();
      setStatus(loginStatus, "", "");
    });
  });

  /* ---------- data loading ---------- */

  function refresh() {
    loadStats();
    loadList();
  }

  function loadStats() {
    fetchJson("/api/admin/stats").then(function (result) {
      if (!result.ok) return;
      statsEls.forEach(function (el) {
        var key = el.getAttribute("data-stat");
        el.textContent = String(result.data[key] !== undefined ? result.data[key] : 0);
      });
    });
  }

  function currentQuery() {
    var params = new URLSearchParams();
    if (searchInput.value.trim()) params.set("q", searchInput.value.trim());
    if (statusFilter.value) params.set("status", statusFilter.value);
    params.set("page", String(state.page));
    params.set("per_page", "10");
    return params.toString();
  }

  function loadList() {
    show(loadingBox, true);
    show(emptyState, false);
    tableBody.innerHTML = "";

    fetchJson("/api/admin/registrations?" + currentQuery()).then(function (result) {
      show(loadingBox, false);
      if (result.status === 401) { showLogin(); return; }
      if (result.status === 503) {
        setStatus(feedback, "error", result.data.detail || "Admin access is not configured.");
        return;
      }
      if (!result.ok) {
        setStatus(feedback, "error", "Could not load registrations. Please refresh to retry.");
        return;
      }
      setStatus(feedback, "", "");

      var data = result.data;
      state.pages = data.pages || 1;
      pageIndicator.textContent = "Page " + data.page + " of " + state.pages;
      pagePrev.disabled = data.page <= 1;
      pageNext.disabled = data.page >= state.pages;

      if (!data.items.length) {
        show(emptyState, true);
        return;
      }

      data.items.forEach(function (item) {
        var tr = document.createElement("tr");
        tr.tabIndex = 0;
        tr.setAttribute("role", "button");
        tr.setAttribute("aria-label", "Open registration " + item.public_reference);

        [
          { text: item.public_reference, cls: "cell-ref" },
          { text: item.full_name },
          { text: item.email },
          { text: experienceLabel(item.experience_type) },
          { text: item.preferred_date || "\u2014" },
          { text: String(item.guest_count) },
          { text: formatDateTime(item.created_at) },
          { text: statusLabel(item.status), cls: "cell-status", attr: ["data-status", item.status] }
        ].forEach(function (spec) {
          var td = document.createElement("td");
          var span = document.createElement("span");
          span.textContent = spec.text;
          if (spec.cls) span.className = spec.cls;
          if (spec.attr) span.setAttribute(spec.attr[0], spec.attr[1]);
          td.appendChild(span);
          tr.appendChild(td);
        });

        function open() { openDetail(item.id); }
        tr.addEventListener("click", open);
        tr.addEventListener("keydown", function (event) {
          if (event.key === "Enter" || event.key === " ") { event.preventDefault(); open(); }
        });
        tableBody.appendChild(tr);
      });
    }).catch(function () {
      show(loadingBox, false);
      setStatus(feedback, "error", "Could not reach the server. Please refresh to retry.");
    });
  }

  /* ---------- detail & status update ---------- */

  function openDetail(id) {
    state.currentId = id;
    setStatus(detailFeedback, "", "");
    detailBody.innerHTML = "";

    fetchJson("/api/admin/registrations/" + id).then(function (result) {
      if (!result.ok) {
        setStatus(detailFeedback, "error", result.data.detail || "Could not load this registration.");
        if (typeof detailDialog.showModal === "function") detailDialog.showModal();
        return;
      }
      var record = result.data;

      var dl = document.createElement("dl");
      buildRow("Reference", record.public_reference).forEach(function (el) { dl.appendChild(el); });
      buildRow("Name", record.full_name).forEach(function (el) { dl.appendChild(el); });
      buildRow("Email", record.email).forEach(function (el) { dl.appendChild(el); });
      buildRow("Experience", experienceLabel(record.experience_type)).forEach(function (el) { dl.appendChild(el); });
      buildRow("Preferred date", record.preferred_date).forEach(function (el) { dl.appendChild(el); });
      buildRow("Guests", record.guest_count).forEach(function (el) { dl.appendChild(el); });
      buildRow("Submitted", formatDateTime(record.created_at)).forEach(function (el) { dl.appendChild(el); });
      buildRow("Last updated", formatDateTime(record.updated_at)).forEach(function (el) { dl.appendChild(el); });
      detailBody.appendChild(dl);

      if (record.notes) {
        var notesTitle = document.createElement("p");
        notesTitle.className = "passport-page-label";
        notesTitle.textContent = "Accessibility / experience notes";
        var notes = document.createElement("div");
        notes.className = "admin-detail-notes";
        notes.textContent = record.notes;
        detailBody.appendChild(notesTitle);
        detailBody.appendChild(notes);
      }

      detailStatus.value = record.status;
      if (typeof detailDialog.showModal === "function") detailDialog.showModal();
    });
  }

  detailSave.addEventListener("click", function () {
    if (state.currentId === null) return;
    detailSave.disabled = true;
    detailSave.textContent = "Saving\u2026";
    setStatus(detailFeedback, "", "");

    fetchJson("/api/admin/registrations/" + state.currentId + "/status", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: detailStatus.value })
    }).then(function (result) {
      if (result.ok) {
        setStatus(detailFeedback, "success", "Status updated to " + statusLabel(result.data.status) + ".");
        loadStats();
        loadList();
      } else if (result.status === 401) {
        setStatus(detailFeedback, "error", "Session expired. Please sign in again.");
        showLogin();
        detailDialog.close();
      } else {
        setStatus(detailFeedback, "error", result.data.detail || "Could not update the status.");
      }
    }).catch(function () {
      setStatus(detailFeedback, "error", "Could not reach the server. Please try again.");
    }).finally(function () {
      detailSave.disabled = false;
      detailSave.textContent = "Save status";
    });
  });

  detailClose.addEventListener("click", function () { detailDialog.close(); });
  detailDialog.addEventListener("click", function (event) {
    if (event.target === detailDialog) detailDialog.close();
  });

  /* ---------- filters, export, pagination ---------- */

  var searchTimer = null;
  searchInput.addEventListener("input", function () {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(function () { state.page = 1; loadList(); }, 300);
  });
  statusFilter.addEventListener("change", function () { state.page = 1; loadList(); });
  pagePrev.addEventListener("click", function () { if (state.page > 1) { state.page--; loadList(); } });
  pageNext.addEventListener("click", function () { if (state.page < state.pages) { state.page++; loadList(); } });

  exportBtn.addEventListener("click", function (event) {
    event.preventDefault();
    var params = new URLSearchParams();
    if (searchInput.value.trim()) params.set("q", searchInput.value.trim());
    if (statusFilter.value) params.set("status", statusFilter.value);
    window.location.href = "/api/admin/registrations/export.csv" + (params.toString() ? "?" + params.toString() : "");
  });

  /* ---------- boot ---------- */

  fetchJson("/api/admin/me").then(function (result) {
    if (result.ok) {
      showDashboard(result.data.email_notifications === "not_configured");
    } else {
      showLogin();
    }
  }).catch(showLogin);

  /* ==========================================================================
     Walk sessions management
     ========================================================================== */

  var sessionNewBtn = document.getElementById("session-new");
  var sessionsFeedback = document.getElementById("sessions-feedback");
  var sessionsTableBody = document.getElementById("sessions-table-body");
  var sessionsEmpty = document.getElementById("sessions-empty");
  var sessionsLoading = document.getElementById("sessions-loading");
  var sessionStatsEls = document.querySelectorAll("[data-sstat]");
  var sessionFormDialog = document.getElementById("session-form-dialog");
  var sessionForm = document.getElementById("session-form");
  var sessionFormTitle = document.getElementById("session-form-title");
  var sessionFormFeedback = document.getElementById("session-form-feedback");
  var sessionFormSave = document.getElementById("session-form-save");
  var sessionFormClose = document.getElementById("session-form-close");
  var sessionDetailDialog = document.getElementById("session-detail-dialog");
  var sessionDetailBody = document.getElementById("session-detail-body");
  var sessionDetailFeedback = document.getElementById("session-detail-feedback");
  var sessionDetailClose = document.getElementById("session-detail-close");

  var editingSessionId = null;

  var SESSION_LABELS = {
    DRAFT: "Draft", PUBLISHED: "Published", CANCELLED: "Cancelled", COMPLETED: "Completed"
  };

  function canEdit(session) {
    return session.status !== "COMPLETED";
  }

  function sessionActionButtons(session) {
    var wrap = document.createElement("div");
    wrap.className = "session-actions-admin";
    function add(label, kind, handler) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "btn btn-small " + kind;
      b.textContent = label;
      b.addEventListener("click", handler);
      wrap.appendChild(b);
      return b;
    }
    if (session.status === "DRAFT") {
      add("Publish", "btn-primary", function () { changeStatus(session, "PUBLISHED"); });
    }
    if (session.status === "PUBLISHED") {
      add("Unpublish", "btn-ghost", function () { changeStatus(session, "DRAFT"); });
    }
    if (session.status === "PUBLISHED" || session.status === "DRAFT") {
      add("Cancel", "btn-ghost", function () { changeStatus(session, "CANCELLED"); });
    }
    if (session.status === "PUBLISHED") {
      add("Complete", "btn-ghost", function () { changeStatus(session, "COMPLETED"); });
    }
    if (canEdit(session)) {
      add("Edit", "btn-ghost", function () { openSessionForm(session); });
      add("Enquiries", "btn-ghost", function () { openSessionDetail(session.id); });
    }
    return wrap;
  }

  function changeStatus(session, status) {
    fetchJson("/api/admin/sessions/" + session.id + "/status", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: status })
    }).then(function (result) {
      if (result.ok) {
        setStatus(sessionsFeedback, "success",
          "Session set to " + SESSION_LABELS[status] + ". " +
          (status === "PUBLISHED"
            ? "It is now visible on the public schedule."
            : "It no longer appears as an available experience on the public schedule."));
        loadSessions();
      } else if (result.status === 401) {
        showLogin();
      } else {
        setStatus(sessionsFeedback, "error", result.data.detail || "Could not update the session status.");
      }
    }).catch(function () {
      setStatus(sessionsFeedback, "error", "Could not reach the server. Please retry.");
    });
  }

  function loadSessions() {
    show(sessionsLoading, true);
    show(sessionsEmpty, false);
    sessionsTableBody.innerHTML = "";

    fetchJson("/api/admin/sessions").then(function (result) {
      show(sessionsLoading, false);
      if (result.status === 401) { showLogin(); return; }
      if (!result.ok) {
        setStatus(sessionsFeedback, "error", "Could not load sessions. Please refresh to retry.");
        return;
      }
      fetchJson("/api/admin/sessions/stats").then(function (statsResult) {
        if (statsResult.ok) {
          sessionStatsEls.forEach(function (el) {
            var key = el.getAttribute("data-sstat");
            el.textContent = String(statsResult.data[key] !== undefined ? statsResult.data[key] : 0);
          });
        }
      });

      var items = result.data.items || [];
      if (!items.length) { show(sessionsEmpty, true); return; }

      items.forEach(function (session) {
        var tr = document.createElement("tr");

        function td(text, cls) {
          var node = document.createElement("td");
          node.textContent = text;
          if (cls) node.className = cls;
          tr.appendChild(node);
          return node;
        }

        td(session.title, "cell-ref");
        td(session.walk_date);
        td(session.start_time);
        td(session.capacity ? "Up to " + session.capacity : "—");
        td(String(session.enquiry_count || 0));

        var statusTd = document.createElement("td");
        var statusSpan = document.createElement("span");
        statusSpan.className = "cell-status";
        statusSpan.setAttribute("data-status", session.status);
        statusSpan.textContent = SESSION_LABELS[session.status] || session.status;
        statusTd.appendChild(statusSpan);
        tr.appendChild(statusTd);

        var actionsTd = document.createElement("td");
        actionsTd.appendChild(sessionActionButtons(session));
        tr.appendChild(actionsTd);

        sessionsTableBody.appendChild(tr);
      });
    }).catch(function () {
      show(sessionsLoading, false);
      setStatus(sessionsFeedback, "error", "Could not reach the server. Please refresh to retry.");
    });
  }

  function openSessionForm(session) {
    editingSessionId = session ? session.id : null;
    sessionFormTitle.textContent = session ? "Edit session" : "New walk session";
    sessionFormSave.textContent = session ? "Save changes" : "Create session";
    setStatus(sessionFormFeedback, "", "");
    document.getElementById("sf-title").value = session ? session.title : "";
    document.getElementById("sf-description").value = session ? session.description : "";
    document.getElementById("sf-date").value = session ? session.walk_date : "";
    document.getElementById("sf-time").value = session ? session.start_time : "";
    document.getElementById("sf-duration").value = session ? session.duration_minutes : 120;
    document.getElementById("sf-capacity").value = session && session.capacity ? session.capacity : "";
    document.getElementById("sf-meeting").value = session ? session.meeting_point : "";
    document.getElementById("sf-inclusions").value = session && session.inclusions ? session.inclusions : "";
    if (typeof sessionFormDialog.showModal === "function") sessionFormDialog.showModal();
  }

  sessionNewBtn.addEventListener("click", function () { openSessionForm(null); });
  sessionFormClose.addEventListener("click", function () { sessionFormDialog.close(); });

  sessionForm.addEventListener("submit", function (event) {
    event.preventDefault();
    var payload = {
      title: document.getElementById("sf-title").value.trim(),
      description: document.getElementById("sf-description").value.trim(),
      walk_date: document.getElementById("sf-date").value,
      start_time: document.getElementById("sf-time").value,
      duration_minutes: parseInt(document.getElementById("sf-duration").value, 10),
      meeting_point: document.getElementById("sf-meeting").value.trim(),
      capacity: document.getElementById("sf-capacity").value
        ? parseInt(document.getElementById("sf-capacity").value, 10)
        : null,
      inclusions: document.getElementById("sf-inclusions").value.trim() || null
    };

    if (!payload.title || !payload.description || !payload.walk_date || !payload.start_time ||
        !payload.meeting_point || isNaN(payload.duration_minutes)) {
      setStatus(sessionFormFeedback, "error", "Please fill in every required field (title, description, date, start time, duration, meeting point).");
      return;
    }

    sessionFormSave.disabled = true;
    sessionFormSave.textContent = "Saving\u2026";
    setStatus(sessionFormFeedback, "", "");

    var request = editingSessionId
      ? fetchJson("/api/admin/sessions/" + editingSessionId, {
          method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
        })
      : fetchJson("/api/admin/sessions", {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
        });

    request.then(function (result) {
      if (result.ok) {
        sessionFormDialog.close();
        setStatus(sessionsFeedback, "success",
          editingSessionId ? "Session updated." : "Session created as a draft. Publish it when the details are verified.");
        loadSessions();
      } else if (result.status === 401) {
        sessionFormDialog.close();
        showLogin();
      } else if (result.status === 422 && Array.isArray(result.data.detail)) {
        setStatus(sessionFormFeedback, "error",
          result.data.detail.map(function (e) { return e.message; }).join(" "));
      } else {
        setStatus(sessionFormFeedback, "error",
          typeof result.data.detail === "string" ? result.data.detail : "Could not save the session. Please review the fields and retry.");
      }
    }).catch(function () {
      setStatus(sessionFormFeedback, "error", "Could not reach the server. Please retry.");
    }).finally(function () {
      sessionFormSave.disabled = false;
      sessionFormSave.textContent = editingSessionId ? "Save changes" : "Create session";
    });
  });

  function openSessionDetail(id) {
    sessionDetailBody.textContent = "";
    setStatus(sessionDetailFeedback, "", "");
    fetchJson("/api/admin/sessions/" + id).then(function (result) {
      if (!result.ok) {
        setStatus(sessionDetailFeedback, "error", result.data.detail || "Could not load this session.");
        if (typeof sessionDetailDialog.showModal === "function") sessionDetailDialog.showModal();
        return;
      }
      var s = result.data.session;

      var dl = document.createElement("dl");
      [
        ["Title", s.title], ["Description", s.description], ["Walk date", s.walk_date],
        ["Start time", s.start_time], ["Duration (min)", s.duration_minutes],
        ["Meeting point", s.meeting_point],
        ["Capacity", s.capacity ? "Up to " + s.capacity + " guests" : "Not set"],
        ["Inclusions / notes", s.inclusions], ["Status", SESSION_LABELS[s.status] || s.status]
      ].forEach(function (pair) {
        var dt = document.createElement("dt");
        dt.textContent = pair[0];
        var dd = document.createElement("dd");
        dd.textContent = pair[1] === null || pair[1] === undefined || pair[1] === "" ? "\u2014" : String(pair[1]);
        dl.appendChild(dt); dl.appendChild(dd);
      });
      sessionDetailBody.appendChild(dl);

      var enquiries = result.data.enquiries.items || [];
      var heading = document.createElement("p");
      heading.className = "passport-page-label";
      heading.textContent = "Enquiries for this session (" + enquiries.length + ")";
      sessionDetailBody.appendChild(heading);

      if (!enquiries.length) {
        sessionDetailBody.appendChild(document.createTextNode("No enquiries yet for this session."));
      } else {
        var list = document.createElement("ul");
        list.className = "session-enquiry-list";
        enquiries.forEach(function (enquiry) {
          var li = document.createElement("li");
          li.textContent =
            enquiry.public_reference + " — " + enquiry.full_name +
            " (" + enquiry.email + "), " + enquiry.guest_count + " guest(s), " +
            enquiry.status;
          list.appendChild(li);
        });
        sessionDetailBody.appendChild(list);
      }

      if (typeof sessionDetailDialog.showModal === "function") sessionDetailDialog.showModal();
    }).catch(function () {
      setStatus(sessionDetailFeedback, "error", "Could not reach the server.");
    });
  }
  sessionDetailClose.addEventListener("click", function () { sessionDetailDialog.close(); });
  sessionDetailDialog.addEventListener("click", function (event) {
    if (event.target === sessionDetailDialog) sessionDetailDialog.close();
  });
})();