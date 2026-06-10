const TRIGGERS = [
  'password',
  'forgot pass',
  'reset pass',
  'change pass',
  'locked out',
  'cannot login',
  "can't login",
  'cannot log in',
  'forgot my login',
  'forgot credentials',
];

export function isPasswordResetRequest(title = '', description = '') {
  const text = `${title} ${description}`.toLowerCase();
  return TRIGGERS.some((t) => text.includes(t));
}