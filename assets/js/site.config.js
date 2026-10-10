/* ==========================================================================
   SHEHARNAAMA — site configuration
   --------------------------------------------------------------------------
   The interest form posts to the FastAPI backend served on the same origin
   (backend/app/main.py). Keep `apiBase` empty for same-origin requests.

   Leave contact/social values as `null` until real ones exist — nothing is
   invented or displayed until then.
   ========================================================================== */

window.SHEHARNAAMA_CONFIG = {
  /* Base URL of the API. Empty string = same origin (recommended: the
     backend serves the frontend too, so no CORS is needed). */
  apiBase: "",

  /* Public contact email, e.g. "hello@sheharnaama.example" — shown in the
     footer once configured. Do not enter a placeholder-looking fake. */
  contactEmail: null,

  /* WhatsApp number in international format, e.g. "9198xxxxxxxx". */
  whatsappNumber: null,

  /* Instagram profile URL for the #WhatLiesBetween campaign.
     Shown in the campaign section only when set. */
  instagramUrl: null
};