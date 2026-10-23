const toggle = document.getElementById('menuToggle');
const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('sidebarOverlay');

function closeSidebar() {
  sidebar?.classList.remove('show');
  overlay?.classList.remove('show');
}

if (toggle && sidebar && overlay) {
  toggle.addEventListener('click', () => {
    sidebar.classList.toggle('show');
    overlay.classList.toggle('show');
  });
  overlay.addEventListener('click', closeSidebar);
}

document.querySelectorAll('.sidebar .nav-link').forEach((link) => {
  link.addEventListener('click', () => {
    if (window.innerWidth < 992) closeSidebar();
  });
});

function onlyDigits(value) {
  return (value || '').replace(/\D/g, '');
}

function applyCpfMask(value) {
  const v = onlyDigits(value).slice(0, 11);
  return v
    .replace(/(\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d{1,2})$/, '$1-$2');
}

function applyPhoneMask(value) {
  const v = onlyDigits(value).replace(/^55/, '').slice(0, 11);
  if (v.length <= 10) return v.replace(/(\d{2})(\d{0,4})(\d{0,4})/, (_, a, b, c) => `(${a}${b ? ') ' + b : ''}${c ? '-' + c : ''}`);
  return v.replace(/(\d{2})(\d{0,5})(\d{0,4})/, (_, a, b, c) => `(${a}${b ? ') ' + b : ''}${c ? '-' + c : ''}`);
}

function applyCepMask(value) {
  const v = onlyDigits(value).slice(0, 8);
  return v.replace(/(\d{5})(\d)/, '$1-$2');
}

document.querySelectorAll('.js-cpf').forEach((input) => {
  input.addEventListener('input', () => input.value = applyCpfMask(input.value));
  input.value = applyCpfMask(input.value);
});

document.querySelectorAll('.js-phone').forEach((input) => {
  input.addEventListener('input', () => input.value = applyPhoneMask(input.value));
  input.value = applyPhoneMask(input.value);
});

document.querySelectorAll('.js-cep').forEach((input) => {
  input.addEventListener('input', () => input.value = applyCepMask(input.value));
  input.value = applyCepMask(input.value);
});

document.querySelectorAll('.js-whatsapp').forEach((input) => {
  input.form?.addEventListener('submit', () => {
    const digits = onlyDigits(input.value).replace(/^55/, '');
    if (digits) input.value = '+55' + digits;
  });
});


const themeToggle = document.getElementById('themeToggle');

function updateThemeIcon(theme) {
  if (!themeToggle) return;
  const icon = themeToggle.querySelector('i');
  if (!icon) return;
  icon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
  themeToggle.setAttribute('title', theme === 'dark' ? 'Ativar tema claro' : 'Ativar tema escuro');
  themeToggle.setAttribute('aria-label', theme === 'dark' ? 'Ativar tema claro' : 'Ativar tema escuro');
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
  updateThemeIcon(theme);
}

const savedTheme = localStorage.getItem('theme') || 'light';
applyTheme(savedTheme);

if (themeToggle) {
  themeToggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    applyTheme(currentTheme === 'dark' ? 'light' : 'dark');
  });
}


const routeChooserModal = document.getElementById('routeChooserModal');
const routeChooserBackdrop = document.getElementById('routeChooserBackdrop');
const routeChooserClose = document.getElementById('routeChooserClose');
const routeChooserCancel = document.getElementById('routeChooserCancel');
const routeGoogleBtn = document.getElementById('routeGoogleBtn');
const routeWazeBtn = document.getElementById('routeWazeBtn');
const routeChooserText = document.getElementById('routeChooserText');

let selectedRouteAddress = '';
let selectedRouteLabel = '';

function closeRouteChooser() {
  routeChooserModal?.setAttribute('hidden', 'hidden');
  routeChooserBackdrop?.setAttribute('hidden', 'hidden');
  routeChooserModal?.setAttribute('aria-hidden', 'true');
}

function openExternalRoute(appName) {
  if (!selectedRouteAddress) return;
  const encoded = encodeURIComponent(selectedRouteAddress);
  const url = appName === 'waze'
    ? `https://waze.com/ul?q=${encoded}&navigate=yes`
    : `https://www.google.com/maps/dir/?api=1&destination=${encoded}`;
  window.open(url, '_blank');
  closeRouteChooser();
}

window.openRouteChooser = function(address, label) {
  if (!address) return;
  selectedRouteAddress = address;
  selectedRouteLabel = label || 'endereço';
  if (routeChooserText) {
    routeChooserText.textContent = `Escolha onde abrir a rota do ${selectedRouteLabel}.`;
  }
  routeChooserModal?.removeAttribute('hidden');
  routeChooserBackdrop?.removeAttribute('hidden');
  routeChooserModal?.setAttribute('aria-hidden', 'false');
};

routeChooserClose?.addEventListener('click', closeRouteChooser);
routeChooserCancel?.addEventListener('click', closeRouteChooser);
routeChooserBackdrop?.addEventListener('click', closeRouteChooser);
routeGoogleBtn?.addEventListener('click', () => openExternalRoute('google'));
routeWazeBtn?.addEventListener('click', () => openExternalRoute('waze'));

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') closeRouteChooser();
});



async function openRiskAlertModal(payload) {
  const modalEl = document.getElementById('riskAlertModal');
  if (!modalEl || !window.bootstrap) return false;
  document.getElementById('riskAlertTitle').textContent = payload.message_title || 'Cliente já possui vínculo com outro credor da rede.';
  document.getElementById('riskAlertAmount').textContent = payload.active_amount || '-';
  document.getElementById('riskAlertLoans').textContent = String(payload.active_loans ?? '-');
  document.getElementById('riskAlertStatus').textContent = payload.status_label || '-';
  const modal = new bootstrap.Modal(modalEl);
  modal.show();
  return await new Promise((resolve) => {
    const continueBtn = document.getElementById('riskAlertContinue');
    const onContinue = () => {
      cleanup();
      modal.hide();
      resolve(true);
    };
    const onHidden = () => {
      cleanup();
      resolve(false);
    };
    const cleanup = () => {
      continueBtn.removeEventListener('click', onContinue);
      modalEl.removeEventListener('hidden.bs.modal', onHidden);
    };
    continueBtn.addEventListener('click', onContinue, { once: true });
    modalEl.addEventListener('hidden.bs.modal', onHidden, { once: true });
  });
}

async function fetchRiskPayload(url) {
  const resp = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
  if (!resp.ok) return { has_alert: false };
  return await resp.json();
}

document.querySelectorAll('.js-risk-client-form').forEach((form) => {
  form.addEventListener('submit', async (ev) => {
    const flag = form.querySelector('input[name="risk_confirmed"]');
    if (flag && flag.value === '1') return;
    ev.preventDefault();
    const cpfInput = form.querySelector('input[name="cpf"]');
    const cpf = cpfInput ? cpfInput.value : '';
    const payload = await fetchRiskPayload('/api/risk-check/client?cpf=' + encodeURIComponent(cpf));
    if (!payload.has_alert) {
      if (flag) flag.value = '1';
      form.submit();
      return;
    }
    const ok = await openRiskAlertModal(payload);
    if (ok) {
      if (flag) flag.value = '1';
      form.submit();
    }
  });
});

document.querySelectorAll('.js-risk-loan-form').forEach((form) => {
  form.addEventListener('submit', async (ev) => {
    const flag = form.querySelector('input[name="risk_confirmed"]');
    if (flag && flag.value === '1') return;
    ev.preventDefault();
    const clientSelect = form.querySelector('select[name="client_id"]');
    const clientId = clientSelect ? clientSelect.value : '';
    const payload = await fetchRiskPayload('/api/risk-check/loan?client_id=' + encodeURIComponent(clientId));
    if (!payload.has_alert) {
      if (flag) flag.value = '1';
      form.submit();
      return;
    }
    const ok = await openRiskAlertModal(payload);
    if (ok) {
      if (flag) flag.value = '1';
      form.submit();
    }
  });
});


function applyWhatsappMask(value) {
  const digits = (value || '').replace(/\D/g, '').slice(0, 11);
  if (digits.length <= 2) return digits ? `(${digits}` : '';
  if (digits.length <= 6) return `(${digits.slice(0,2)}) ${digits.slice(2)}`;
  if (digits.length <= 10) return `(${digits.slice(0,2)}) ${digits.slice(2,6)}-${digits.slice(6)}`;
  return `(${digits.slice(0,2)}) ${digits.slice(2,7)}-${digits.slice(7,11)}`;
}

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.js-whatsapp-mask').forEach(function (input) {
    input.addEventListener('input', function () {
      this.value = applyWhatsappMask(this.value);
    });
    input.value = applyWhatsappMask(input.value);
  });
});
