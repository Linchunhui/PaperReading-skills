(() => {
  const picker = document.getElementById('theme-select');
  const system = matchMedia('(prefers-color-scheme: dark)');
  let choice = 'system';
  try { choice = localStorage.getItem('image-acceleration-theme') || 'system'; } catch (_) {}
  if (!['system','light','dark'].includes(choice)) choice = 'system';
  picker.value = choice;
  function apply() { document.documentElement.dataset.theme = choice === 'system' ? (system.matches ? 'dark' : 'light') : choice; }
  picker.addEventListener('change', () => { choice = picker.value; try { localStorage.setItem('image-acceleration-theme', choice); } catch (_) {} apply(); });
  system.addEventListener('change', () => { if (choice === 'system') apply(); });
  apply();
})();
