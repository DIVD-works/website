
const toggle = document.querySelector('.nav-toggle');
const nav = document.querySelector('#primary-nav');

if (toggle && nav) {
  toggle.addEventListener('click', () => {
    const open = nav.classList.toggle('is-open');
    toggle.setAttribute('aria-expanded', String(open));
  });

  nav.addEventListener('click', (event) => {
    if (event.target instanceof HTMLAnchorElement) {
      nav.classList.remove('is-open');
      toggle.setAttribute('aria-expanded', 'false');
    }
  });
}

(() => {
  const canvas = document.getElementById('hero-mesh');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const hero = canvas.closest('.hero');
  let W = 1;
  let H = 1;
  let DPR = 1;
  let raf = 0;
  let mouseX = 0.5;
  let mouseY = 0.5;
  let isActive = false;

  const ROWS = 36;
  const SAMPLES = 240;
  const COLS = 18;
  const COLOR = '255, 211, 38';

  function resize() {
    const rect = canvas.getBoundingClientRect();
    W = Math.max(1, rect.width);
    H = Math.max(1, rect.height);
    DPR = Math.min(window.devicePixelRatio || 1, 2);

    canvas.width = Math.round(W * DPR);
    canvas.height = Math.round(H * DPR);
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }

  function surface(progress, depth, time) {
    const rawX = -90 + progress * (W + 180);
    const horizon = H * (W < 720 ? 0.50 : 0.47);
    const perspective = Math.pow(depth, 1.72);
    const baseY = horizon + perspective * (H - horizon + 165);

    const amp = 10 + Math.pow(depth, 1.72) * (W < 720 ? 62 : 92);

    // These time terms make the surface continuously change shape.
    const longWave =
      Math.sin(rawX * 0.0030 - time * 0.36 + depth * 4.0) *
      amp * 0.72;

    const wave1 =
      Math.sin(rawX * 0.0085 + time * 0.95 + depth * 2.4) *
      amp * 0.42;

    const wave2 =
      Math.sin(rawX * 0.0168 - time * 0.58 + depth * 5.3) *
      amp * 0.24;

    const wave3 =
      Math.cos(rawX * 0.0044 + time * 0.44 - depth * 3.2) *
      amp * 0.30;

    const travellingPeak =
      Math.sin(rawX * 0.0018 - time * 0.25) *
      Math.sin(rawX * 0.0065 + time * 0.48 + depth * 2.0) *
      amp * 0.28;

    const px = (mouseX - 0.5) * 30 * depth;
    const py = (mouseY - 0.5) * 14 * depth;

    return {
      x: rawX + px,
      y: baseY + longWave + wave1 + wave2 + wave3 + travellingPeak + py
    };
  }

  function draw(ms) {
    const t = ms * 0.001;

    ctx.clearRect(0, 0, W, H);
    ctx.save();
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    // Horizontal flowing lines.
    ctx.shadowColor = `rgba(${COLOR}, .34)`;
    ctx.shadowBlur = W < 720 ? 4 : 8;

    for (let row = 0; row < ROWS; row++) {
      const depth = row / (ROWS - 1);
      ctx.beginPath();

      for (let i = 0; i <= SAMPLES; i++) {
        const p = surface(i / SAMPLES, depth, t);
        if (i === 0) ctx.moveTo(p.x, p.y);
        else ctx.lineTo(p.x, p.y);
      }

      ctx.strokeStyle = `rgba(${COLOR}, ${0.36 + depth * 0.62})`;
      ctx.lineWidth = 1.05 + depth * 1.1;
      ctx.stroke();
    }

    // Connecting lines, intentionally subtle.
    ctx.shadowBlur = 2;
    for (let col = 0; col <= COLS; col++) {
      const progress = col / COLS;
      ctx.beginPath();

      for (let row = 0; row < ROWS; row++) {
        const depth = row / (ROWS - 1);
        const p = surface(progress, depth, t);
        if (row === 0) ctx.moveTo(p.x, p.y);
        else ctx.lineTo(p.x, p.y);
      }

      ctx.strokeStyle = `rgba(${COLOR}, .14)`;
      ctx.lineWidth = .8;
      ctx.stroke();
    }

    ctx.restore();
    raf = requestAnimationFrame(draw);
  }

  function start() {
    cancelAnimationFrame(raf);
    resize();
    if (!isActive) return;
    raf = requestAnimationFrame(draw);
  }

  function setActive(active) {
    isActive = active;
    if (!active) {
      cancelAnimationFrame(raf);
      raf = 0;
      return;
    }
    start();
  }

  if (hero) {
    const observer = new IntersectionObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      setActive(entry.isIntersecting);
    }, { threshold: 0.15 });

    observer.observe(hero);
  } else {
    setActive(true);
  }

  window.addEventListener('resize', start, { passive: true });
  window.addEventListener('pointermove', (event) => {
    mouseX = event.clientX / Math.max(1, window.innerWidth);
    mouseY = event.clientY / Math.max(1, window.innerHeight);
  }, { passive: true });

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) setActive(false);
    else if (hero && hero.getBoundingClientRect().top < window.innerHeight) setActive(true);
    else setActive(Boolean(hero && hero.isConnected));
  });

  setActive(true);
})();
