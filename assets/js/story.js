/**
 * SHEHARNAAMA — 30-Minute Sample Story Experience
 * Interactive Audio Engine, Chapter Navigation, Digital Passport Stamp
 */

(function () {
  'use strict';

  const TOTAL_DURATION_SEC = 1800; // 30 minutes

  const CHAPTERS = [
    { id: 'ch1', title: 'The Wooden Threshold', start: 0, tag: 'Architecture' },
    { id: 'ch2', title: 'The Rhythm of Beaten Copper', start: 495, tag: 'Craft' }, // 08:15
    { id: 'ch3', title: 'The Brass Samovar & Spices', start: 990, tag: 'Food & Aroma' }, // 16:30
    { id: 'ch4', title: 'What the Walls Remember', start: 1450, tag: 'Everyday Life' } // 24:10
  ];

  let isPlaying = false;
  let currentTime = 0;
  let playbackRate = 1.0;
  let timerInterval = null;

  // Web Audio Context for authentic ambient soundscape
  let audioCtx = null;
  let ambientOsc1 = null;
  let ambientOsc2 = null;
  let ambientGain = null;
  let chimeInterval = null;

  function initAudio() {
    if (!audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        audioCtx = new AudioContext();
      }
    }
    if (audioCtx && audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
  }

  function startAmbientSound() {
    if (!audioCtx) return;
    try {
      ambientGain = audioCtx.createGain();
      ambientGain.gain.setValueAtTime(0.04, audioCtx.currentTime);
      ambientGain.connect(audioCtx.destination);

      // Warm calming drone (root D3 / A3)
      ambientOsc1 = audioCtx.createOscillator();
      ambientOsc1.type = 'sine';
      ambientOsc1.frequency.setValueAtTime(146.83, audioCtx.currentTime); // D3
      ambientOsc1.connect(ambientGain);
      ambientOsc1.start();

      ambientOsc2 = audioCtx.createOscillator();
      ambientOsc2.type = 'triangle';
      ambientOsc2.frequency.setValueAtTime(220.00, audioCtx.currentTime); // A3
      ambientOsc2.connect(ambientGain);
      ambientOsc2.start();

      // Subtle metallic copper chime every ~6 seconds
      chimeInterval = setInterval(() => {
        if (!isPlaying || !audioCtx) return;
        playCopperChime();
      }, 5500);
    } catch (e) {
      console.warn('Ambient audio could not start:', e);
    }
  }

  function playCopperChime() {
    if (!audioCtx) return;
    try {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = 'sine';
      // Harmonic chime of hand-beaten brass
      osc.frequency.setValueAtTime(880 + Math.random() * 80, audioCtx.currentTime);
      gain.gain.setValueAtTime(0.03, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 1.2);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 1.2);
    } catch (e) {}
  }

  function stopAmbientSound() {
    if (chimeInterval) clearInterval(chimeInterval);
    if (ambientOsc1) { try { ambientOsc1.stop(); } catch(e){} ambientOsc1 = null; }
    if (ambientOsc2) { try { ambientOsc2.stop(); } catch(e){} ambientOsc2 = null; }
    if (ambientGain) { ambientGain = null; }
  }

  function formatTime(sec) {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }

  function updateUI() {
    const scrubber = document.getElementById('audio-scrubber');
    const timeCurrent = document.getElementById('time-current');
    const playBtn = document.getElementById('btn-play-pause');
    const playIcon = document.getElementById('play-icon');
    const pauseIcon = document.getElementById('pause-icon');
    const trackTitle = document.getElementById('active-chapter-title');

    if (scrubber) scrubber.value = currentTime;
    if (timeCurrent) timeCurrent.textContent = formatTime(currentTime);

    // Active chapter detection
    let activeCh = CHAPTERS[0];
    for (let i = CHAPTERS.length - 1; i >= 0; i--) {
      if (currentTime >= CHAPTERS[i].start) {
        activeCh = CHAPTERS[i];
        break;
      }
    }

    if (trackTitle) {
      trackTitle.textContent = `${activeCh.title} (${activeCh.tag})`;
    }

    // Highlight card
    document.querySelectorAll('.chapter-card').forEach((card) => {
      card.classList.toggle('highlighted', card.id === activeCh.id);
    });

    // Highlight pill button
    document.querySelectorAll('.chapter-jump-btn').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.chapter === activeCh.id);
    });

    if (playIcon && pauseIcon) {
      playIcon.style.display = isPlaying ? 'none' : 'block';
      pauseIcon.style.display = isPlaying ? 'block' : 'none';
    }
  }

  function togglePlay() {
    initAudio();
    isPlaying = !isPlaying;

    if (isPlaying) {
      startAmbientSound();
      timerInterval = setInterval(() => {
        currentTime += 1 * playbackRate;
        if (currentTime >= TOTAL_DURATION_SEC) {
          currentTime = TOTAL_DURATION_SEC;
          togglePlay();
        }
        updateUI();
      }, 1000);
    } else {
      stopAmbientSound();
      if (timerInterval) clearInterval(timerInterval);
    }
    updateUI();
  }

  function seekTo(seconds) {
    currentTime = Math.max(0, Math.min(TOTAL_DURATION_SEC, seconds));
    updateUI();
  }

  // DOM bindings
  document.addEventListener('DOMContentLoaded', () => {
    const playBtn = document.getElementById('btn-play-pause');
    const scrubber = document.getElementById('audio-scrubber');
    const speedBtn = document.getElementById('btn-speed');

    if (playBtn) {
      playBtn.addEventListener('click', togglePlay);
    }

    if (scrubber) {
      scrubber.addEventListener('input', (e) => {
        seekTo(Number(e.target.value));
      });
    }

    if (speedBtn) {
      speedBtn.addEventListener('click', () => {
        if (playbackRate === 1.0) playbackRate = 1.25;
        else if (playbackRate === 1.25) playbackRate = 1.5;
        else playbackRate = 1.0;
        speedBtn.textContent = `${playbackRate}x`;
      });
    }

    // Chapter jump pills
    document.querySelectorAll('.chapter-jump-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const chId = btn.dataset.chapter;
        const target = CHAPTERS.find(c => c.id === chId);
        if (target) {
          seekTo(target.start);
          const card = document.getElementById(chId);
          if (card) {
            card.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        }
      });
    });

    // Passport Stamp Interaction
    const stampBtn = document.getElementById('btn-collect-stamp');
    const stampSeal = document.getElementById('stamp-seal');
    const savedStamp = localStorage.getItem('sheharnaama_stamp_stop03');

    function applyStamp() {
      if (stampSeal) stampSeal.classList.add('stamped');
      if (stampBtn) {
        stampBtn.textContent = '✓ Passport Stamped';
        stampBtn.classList.add('done');
      }
      localStorage.setItem('sheharnaama_stamp_stop03', 'true');
    }

    if (savedStamp === 'true') {
      applyStamp();
    }

    if (stampBtn) {
      stampBtn.addEventListener('click', () => {
        initAudio();
        // Play physical stamping sound via Web Audio
        if (audioCtx) {
          try {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.frequency.setValueAtTime(120, audioCtx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(40, audioCtx.currentTime + 0.15);
            gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.15);
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.15);
          } catch(e){}
        }
        applyStamp();
      });
    }

    // Memory Note Interaction
    const noteArea = document.getElementById('user-memory-note');
    const saveNoteBtn = document.getElementById('btn-save-note');
    const noteStatus = document.getElementById('note-save-status');

    if (noteArea) {
      const savedNote = localStorage.getItem('sheharnaama_note_stop03');
      if (savedNote) noteArea.value = savedNote;
    }

    if (saveNoteBtn && noteArea) {
      saveNoteBtn.addEventListener('click', () => {
        localStorage.setItem('sheharnaama_note_stop03', noteArea.value);
        if (noteStatus) {
          noteStatus.textContent = 'Saved to your device!';
          noteStatus.style.display = 'inline';
          setTimeout(() => { noteStatus.style.display = 'none'; }, 3000);
        }
      });
    }

    updateUI();
  });
})();
