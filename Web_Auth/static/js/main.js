// Web_Auth — client-side JavaScript

// ── Password visibility toggle ────────────────────────────────────────────
function togglePassword(inputId) {
  const input = document.getElementById(inputId);
  if (!input) return;
  input.type = input.type === 'password' ? 'text' : 'password';
}

// ── Password strength meter ───────────────────────────────────────────────
const passwordInput = document.getElementById('password');
const strengthBar   = document.getElementById('password-strength');

if (passwordInput && strengthBar) {
  passwordInput.addEventListener('input', () => {
    const val = passwordInput.value;
    strengthBar.className = 'password-strength';
    if (val.length === 0) return;
    if (val.length < 6)  { strengthBar.classList.add('weak'); return; }
    const hasUpper  = /[A-Z]/.test(val);
    const hasLower  = /[a-z]/.test(val);
    const hasDigit  = /\d/.test(val);
    const hasSpecial = /[^A-Za-z0-9]/.test(val);
    const score = [hasUpper, hasLower, hasDigit, hasSpecial].filter(Boolean).length;
    if (score <= 2) strengthBar.classList.add('weak');
    else if (score === 3) strengthBar.classList.add('medium');
    else strengthBar.classList.add('strong');
  });
}

// ── Confirm password match ────────────────────────────────────────────────
const confirmInput = document.getElementById('confirm_password');
const matchHint    = document.getElementById('match-hint');

if (confirmInput && passwordInput && matchHint) {
  confirmInput.addEventListener('input', () => {
    if (confirmInput.value.length === 0) {
      matchHint.classList.add('hidden');
      return;
    }
    matchHint.classList.remove('hidden', 'match', 'no-match');
    if (confirmInput.value === passwordInput.value) {
      matchHint.textContent = '✓ Passwords match';
      matchHint.classList.add('match');
    } else {
      matchHint.textContent = '✗ Passwords do not match';
      matchHint.classList.add('no-match');
    }
  });
}

// ── Form submit loading state ─────────────────────────────────────────────
function attachLoadingState(formId, btnId) {
  const form = document.getElementById(formId);
  const btn  = document.getElementById(btnId);
  if (!form || !btn) return;
  form.addEventListener('submit', (e) => {
    const btnText   = btn.querySelector('.btn-text');
    const btnLoader = btn.querySelector('.btn-loader');
    if (btnText)   btnText.classList.add('hidden');
    if (btnLoader) btnLoader.classList.remove('hidden');
    btn.disabled = true;
  });
}

attachLoadingState('login-form', 'login-btn');
attachLoadingState('register-form', 'register-btn');

// ── Auto-dismiss alerts after 5 seconds ──────────────────────────────────
['success-alert', 'info-alert'].forEach(id => {
  const el = document.getElementById(id);
  if (el) {
    setTimeout(() => {
      el.style.transition = 'opacity 0.5s ease';
      el.style.opacity    = '0';
      setTimeout(() => el.remove(), 500);
    }, 5000);
  }
});
