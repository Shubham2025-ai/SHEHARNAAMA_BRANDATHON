/* ==========================================================================
   SHEHARNAAMA — interactions
   ========================================================================== */

(function () {
  "use strict";

  var config = window.SHEHARNAAMA_CONFIG || {};

  /* ---------- Sticky header shadow ---------- */

  var header = document.getElementById("site-header");

  function onScrollHeader() {
    if (!header) return;
    header.classList.toggle("scrolled", window.scrollY > 8);
  }
  onScrollHeader();

  /* ---------- Mobile navigation ---------- */

  var navToggle = document.getElementById("nav-toggle");
  var mainNav = document.getElementById("main-nav");

  function closeNav() {
    if (!mainNav || !navToggle) return;
    mainNav.classList.remove("open");
    navToggle.setAttribute("aria-expanded", "false");
    navToggle.setAttribute("aria-label", "Open menu");
  }

  if (navToggle && mainNav) {
    navToggle.addEventListener("click", function () {
      var isOpen = mainNav.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", String(isOpen));
      navToggle.setAttribute("aria-label", isOpen ? "Close menu" : "Open menu");
    });

    mainNav.addEventListener("click", function (event) {
      if (event.target.closest("a")) closeNav();
    });

    document.addEventListener("click", function (event) {
      if (
        mainNav.classList.contains("open") &&
        !mainNav.contains(event.target) &&
        !navToggle.contains(event.target)
      ) {
        closeNav();
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && mainNav.classList.contains("open")) {
        closeNav();
        navToggle.focus();
      }
    });
  }

  /* ---------- Back to top ---------- */

  var toTop = document.getElementById("to-top");

  function onScrollToTop() {
    if (!toTop) return;
    toTop.classList.toggle("show", window.scrollY > 640);
  }
  onScrollToTop();

  if (toTop) {
    toTop.addEventListener("click", function () {
      var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
      document.getElementById("top").focus({ preventScroll: true });
    });
  }

  window.addEventListener("scroll", function () {
    onScrollHeader();
    onScrollToTop();
  }, { passive: true });

  /* ---------- Reveal on scroll ---------- */

  var revealEls = document.querySelectorAll("[data-reveal]");
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if ("IntersectionObserver" in window && !reduceMotion) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("in-view");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });

    revealEls.forEach(function (el) { observer.observe(el); });

    /* Deterministic first paint: reveal anything already inside the
       viewport instead of waiting for the observer callback. */
    revealEls.forEach(function (el) {
      var rect = el.getBoundingClientRect();
      if (rect.top < window.innerHeight && rect.bottom > 0) {
        el.classList.add("in-view");
        observer.unobserve(el);
      }
    });
  } else {
    revealEls.forEach(function (el) { el.classList.add("in-view"); });
  }

  /* ---------- Story Passport flip ---------- */

  var flipBtn = document.getElementById("passport-flip");
  var book = document.getElementById("passport-book");

  if (flipBtn && book) {
    flipBtn.addEventListener("click", function () {
      var flipped = book.classList.toggle("flipped");
      flipBtn.setAttribute("aria-pressed", String(flipped));
      flipBtn.textContent = flipped ? "View cover" : "Look inside";
    });
  }

  /* ---------- Gallery lightbox ---------- */

  var lightbox = document.getElementById("lightbox");
  var lightboxImg = document.getElementById("lightbox-img");
  var lightboxCaption = document.getElementById("lightbox-caption");
  var lightboxClose = document.getElementById("lightbox-close");

  if (
    lightbox && lightboxImg && lightboxCaption && lightboxClose &&
    typeof lightbox.showModal === "function"
  ) {
    document.querySelectorAll(".gallery-trigger").forEach(function (trigger) {
      trigger.addEventListener("click", function () {
        var img = trigger.querySelector("img");
        if (!img) return;
        lightboxImg.src = img.currentSrc || img.src;
        lightboxImg.alt = img.alt;
        lightboxCaption.textContent = trigger.getAttribute("data-caption") || "";
        lightbox.showModal();
      });
    });

    lightboxClose.addEventListener("click", function () {
      lightbox.close();
    });

    lightbox.addEventListener("click", function (event) {
      if (event.target === lightbox) lightbox.close();
    });

    lightbox.addEventListener("close", function () {
      lightboxImg.src = "";
    });
  } else {
    /* Graceful fallback: hide triggers so controls are never decorative */
document.querySelectorAll(".gallery-trigger").forEach(function (trigger) {
      trigger.disabled = true;
      trigger.style.cursor = "default";
    });
  }

  /* ---------- Footer year ---------- */

  var year = document.getElementById("year");
  if (year) year.textContent = String(new Date().getFullYear());

  /* ---------- Config-driven footer contact ---------- */

  var contactSlot = document.getElementById("footer-contact-details");
  if (contactSlot) {
    var bits = [];
    if (config.contactEmail) {
      bits.push('<a href="mailto:' + config.contactEmail + '">' + config.contactEmail + "</a>");
    }
    if (config.whatsappNumber) {
      bits.push('<a href="https://wa.me/' + config.whatsappNumber + '">WhatsApp</a>');
    }
    if (bits.length) {
      contactSlot.innerHTML = "<p>" + bits.join(" · ") + "</p>";
    }
  }

  /* ---------- Instagram link when configured ---------- */

  var instaSlot = document.getElementById("campaign-insta-slot");
  if (instaSlot && config.instagramUrl && /^https:\/\/(www\.)?instagram\.com\//.test(config.instagramUrl)) {
    var link = document.createElement("a");
    link.href = config.instagramUrl;
    link.className = "btn btn-light btn-small";
    link.rel = "noopener";
    link.textContent = "Follow #WhatLiesBetween";
    instaSlot.appendChild(link);
  }

  /* ---------- Interest form ---------- */

  var form = document.getElementById("interest-form");

  if (form) {
    var guestsSelect = document.getElementById("f-guests");
    var submitBtn = document.getElementById("form-submit");
    var statusBox = document.getElementById("form-status");
    var isSubmitting = false;

    /* Idempotency: one key per form session, reused on retries so an
       accidental double-submit (or a retry after a timeout that actually
       succeeded) cannot create duplicate records. Rotated after success. */
    function newIdempotencyKey() {
      if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID().replace(/-/g, "");
      return "ik-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 14);
    }
    var idempotencyKey = newIdempotencyKey();

    /* Populate guest options 1–12 */
    if (guestsSelect) {
      for (var i = 1; i <= 12; i++) {
        var opt = document.createElement("option");
        opt.value = String(i);
        opt.textContent = i + (i === 1 ? " guest" : " guests");
        guestsSelect.appendChild(opt);
      }
    }

    var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

    function setError(input, errorEl, message) {
      errorEl.textContent = message || "";
      if (message) {
        input.classList.add("invalid");
        input.setAttribute("aria-invalid", "true");
      } else {
        input.classList.remove("invalid");
        input.removeAttribute("aria-invalid");
      }
    }

    function validate() {
      var ok = true;
      var firstInvalid = null;

      var name = document.getElementById("f-name");
      var email = document.getElementById("f-email");
      var guests = document.getElementById("f-guests");
      var interest = document.getElementById("f-interest");
      var consent = document.getElementById("f-consent");
      var errName = document.getElementById("err-name");
      var errEmail = document.getElementById("err-email");
      var errGuests = document.getElementById("err-guests");
      var errInterest = document.getElementById("err-interest");
      var errConsent = document.getElementById("err-consent");

      function check(input, errEl, message, valid) {
        setError(input, errEl, valid ? "" : message);
        if (!valid) {
          ok = false;
          if (!firstInvalid) firstInvalid = input;
        }
      }

      check(name, errName, "Please enter your full name.", name.value.trim().length >= 2);

      var emailVal = email.value.trim();
      check(email, errEmail, "Please enter a valid email address, e.g. name@example.com.", EMAIL_RE.test(emailVal));

      check(guests, errGuests, "Please select the number of guests.", guests.value !== "");

      check(interest, errInterest, "Please choose an experience.", interest.value !== "");

      setError(consent, errConsent, consent.checked ? "" : "Please confirm you understand this is not a booking.");
      if (!consent.checked) {
        ok = false;
        if (!firstInvalid) firstInvalid = consent;
      }

      if (firstInvalid) firstInvalid.focus();
      return ok;
    }

    /* Clear individual errors as the user fixes them */
    [
      ["f-name", "err-name"],
      ["f-email", "err-email"],
      ["f-guests", "err-guests"],
      ["f-interest", "err-interest"]
    ].forEach(function (pair) {
      var el = document.getElementById(pair[0]);
      var err = document.getElementById(pair[1]);
      if (el && err) {
        el.addEventListener("input", function () { setError(el, err, ""); });
        el.addEventListener("change", function () { setError(el, err, ""); });
      }
    });

    var consentInput = document.getElementById("f-consent");
    var consentErr = document.getElementById("err-consent");
    if (consentInput && consentErr) {
      consentInput.addEventListener("change", function () {
        setError(consentInput, consentErr, "");
      });
    }

    function showStatus(kind, html, moveFocus) {
      statusBox.innerHTML = '<div class="status-box status-' + kind + '">' + html + "</div>";
      var box = statusBox.querySelector(".status-box");
      if (box && moveFocus !== false) {
        box.setAttribute("tabindex", "-1");
        box.focus({ preventScroll: false });
      }
    }

    /* Server-generated reference display and honest failure states. */
    var FIELD_ERROR_IDS = {
      full_name: ["f-name", "err-name"],
      email: ["f-email", "err-email"],
      guest_count: ["f-guests", "err-guests"],
      experience_type: ["f-interest", "err-interest"],
      session_id: ["f-session", null],
      preferred_date: ["f-date", null],
      notes: ["f-notes", null],
      consent: ["f-consent", "err-consent"]
    };

    function applyServerFieldErrors(detail) {
      var handled = false;
      if (Array.isArray(detail)) {
        detail.forEach(function (item) {
          var field = item && item.field;
          var message = item && item.message ? item.message : "Invalid value.";
          var mapping = FIELD_ERROR_IDS[field];
          if (mapping) {
            var input = document.getElementById(mapping[0]);
            var errEl = mapping[1] ? document.getElementById(mapping[1]) : null;
            if (input) {
              input.classList.add("invalid");
              input.setAttribute("aria-invalid", "true");
            }
            if (errEl) errEl.textContent = message;
            handled = true;
          }
        });
      }
      return handled;
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();

      if (isSubmitting) return; /* block rapid duplicate submissions */

      statusBox.innerHTML = "";

      if (!validate()) {
        showStatus("error", "Almost there. Please fix the highlighted fields and try again. Your answers are still saved in the form.", false);
        return;
      }

      isSubmitting = true;
      submitBtn.disabled = true;
      var originalLabel = submitBtn.textContent;
      submitBtn.textContent = "Registering\u2026";

      var payload = {
        full_name: document.getElementById("f-name").value.trim(),
        email: document.getElementById("f-email").value.trim(),
        preferred_date: document.getElementById("f-date").value || null,
        guest_count: parseInt(guestsSelect.value, 10),
        experience_type: document.getElementById("f-interest").value,
        notes: document.getElementById("f-notes").value.trim() || null,
        consent: document.getElementById("f-consent").checked,
        session_id: window.SheharnaamaSessions ? window.SheharnaamaSessions.getSelectedId() : null,
        website: document.getElementById("f-website") ? document.getElementById("f-website").value : ""
      };

      fetch(config.apiBase + "/api/registrations", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Idempotency-Key": idempotencyKey
        },
        body: JSON.stringify(payload)
      })
        .then(function (response) {
          return response.json().catch(function () { return {}; }).then(function (data) {
            return { ok: response.ok, status: response.status, data: data };
          });
        })
        .then(function (result) {
          if (result.ok && result.data && result.data.reference) {
            var reference = String(result.data.reference); /* generated by the server */
            var box = document.createElement("div");
            box.className = "status-box status-success";
            var lead = document.createElement("strong");
            lead.textContent = "Thank you! Your interest has been recorded successfully. " +
              "Your reference is " + reference + ".";
            box.appendChild(lead);
            box.appendChild(document.createElement("br"));
            box.appendChild(document.createTextNode(
              "This is an expression of interest, not a confirmed tour booking. " +
              "Availability and final details will be communicated separately."
            ));
            if (result.data.session && result.data.session.title) {
              var s = result.data.session;
              var dateParts = String(s.walk_date).split("-");
              var prettyDate = dateParts.length === 3
                ? parseInt(dateParts[2], 10) + "/" + dateParts[1] + "/" + dateParts[0]
                : s.walk_date;
              box.appendChild(document.createElement("br"));
              box.appendChild(document.createTextNode(
                "Session selected: " + s.title + " — " + prettyDate +
                (s.meeting_point ? ", meeting point: " + s.meeting_point : "")
              ));
              box.appendChild(document.createElement("br"));
              box.appendChild(document.createTextNode(
                "The meeting-point details above are provisional until the walk is confirmed."
              ));
            }
            if (result.data.email_notifications === "not_configured") {
              box.appendChild(document.createElement("br"));
              box.appendChild(document.createTextNode(
                "Automated emails are not configured, so the team follows up manually."
              ));
            }
            statusBox.innerHTML = "";
            statusBox.appendChild(box);
            box.setAttribute("tabindex", "-1");
            box.focus({ preventScroll: false });
            form.reset();
            if (window.SheharnaamaSessions) window.SheharnaamaSessions.reload();
            idempotencyKey = newIdempotencyKey(); /* fresh key for a new enquiry */
          } else if (result.status === 400 || result.status === 422) {
            var mapped = applyServerFieldErrors(result.data.detail);
            showStatus("error", mapped
              ? "Please correct the highlighted fields and try again."
              : (typeof result.data.detail === "string" ? result.data.detail : "Registration could not be accepted. Please review your answers and try again."));
          } else if (result.status === 429) {
            showStatus("error", "Too many submissions right now. Please wait a minute and try again — your answers are still in the form.");
          } else if (result.status === 503) {
            showStatus("error", "The registration service is not available on this deployment. Nothing has been saved. Please contact the team directly.");
          } else {
            showStatus("error", "We could not save your registration. Nothing has been recorded yet — your answers are still in the form, please try again.");
          }
        })
        .catch(function () {
          /* Server unreachable: honest failure, keep data for retry. */
          showStatus("error", "We could not reach the registration service. Nothing has been saved. Your answers are still in the form — please try again in a moment.");
        })
        .finally(function () {
          isSubmitting = false;
          submitBtn.disabled = false;
          submitBtn.textContent = originalLabel;
        });
    });
  }
})();