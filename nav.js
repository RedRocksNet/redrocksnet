/* RedRocks Net - Navigation Module (System A) */
(() => {
  const mount = document.getElementById("rr-nav-mount");
  if (!mount) return;

  const current = (mount.getAttribute("data-current") || "").trim();

  // A nav structure (simple)
  const navHTML = `
    <nav class="rr-nav" aria-label="Primary">
      <a class="rr-nav-link" data-key="home" href="/">首页</a>
      <a class="rr-nav-link" data-key="gallery" href="/gallery.html">摄影作品</a>
      <a class="rr-nav-link" data-key="sutras" href="/sutras.html">佛经手书</a>
      <a class="rr-nav-link" data-key="articles" href="/articles.html">随笔</a>
      <a class="rr-nav-link" data-key="about" href="/about.html">关于我</a>
    </nav>
  `.trim();

  mount.innerHTML = navHTML;

  // Highlight current page
  if (current) {
    const links = mount.querySelectorAll(".rr-nav-link");
    links.forEach((a) => {
      if (a.getAttribute("data-key") === current) {
        a.setAttribute("aria-current", "page");
      } else {
        a.removeAttribute("aria-current");
      }
    });
  }

  // Auto-hide after idle (same behavior style as your original index)
  const nav = mount.querySelector(".rr-nav");
  if (!nav) return;

  let timeoutId = null;

  const showNav = () => nav.classList.remove("hidden");
  const hideNav = () => nav.classList.add("hidden");

  const scheduleHide = () => {
    if (timeoutId) clearTimeout(timeoutId);
    timeoutId = setTimeout(hideNav, 3000);
  };

  const onActivity = () => {
    showNav();
    scheduleHide();
  };

  window.addEventListener("mousemove", onActivity, { passive: true });
  window.addEventListener("keydown", onActivity);
  window.addEventListener("scroll", onActivity, { passive: true });

  // initial hide timer
  scheduleHide();
})();