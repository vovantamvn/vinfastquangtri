// Count call/zalo clicks in GoatCounter (only when its script is enabled in index.html).
document.addEventListener('click', function (e) {
  var a = e.target.closest('[data-track]');
  if (a && window.goatcounter && window.goatcounter.count) {
    window.goatcounter.count({ path: 'click-' + a.dataset.track, title: a.textContent.trim(), event: true });
  }
});
