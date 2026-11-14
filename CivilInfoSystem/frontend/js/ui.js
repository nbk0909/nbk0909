/* =============================================================================
   أدوات الواجهة: التنسيق العربي، والإشعارات، وبناء العناصر
   ============================================================================= */

const UI = (() => {
  'use strict';

  const ARABIC_DIGITS = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'];

  /* ---------------------------------------------------------------------
     الهروب من HTML
     ------------------------------------------------------------------ */

  /**
   * يحوّل النص إلى صيغة آمنة للإدراج في HTML.
   * كل قيمة قادمة من الخادم تمرّ من هنا: أسماء الأشخاص بيانات يُدخلها
   * موظفون، ولو أُدرجت كما هي لأمكن حقن سكربت عبر حقل الاسم.
   */
  function escape(value) {
    if (value === null || value === undefined) return '';
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  /* ---------------------------------------------------------------------
     الأرقام والتواريخ
     ------------------------------------------------------------------ */

  function preferArabicNumerals() {
    return localStorage.getItem('numerals') === 'arabic';
  }

  function digits(value) {
    const text = String(value ?? '');
    if (!preferArabicNumerals()) return text;
    return text.replace(/[0-9]/g, (d) => ARABIC_DIGITS[Number(d)]);
  }

  const MONTHS = [
    'كانون الثاني', 'شباط', 'آذار', 'نيسان', 'أيار', 'حزيران',
    'تموز', 'آب', 'أيلول', 'تشرين الأول', 'تشرين الثاني', 'كانون الأول',
  ];

  function formatDate(value, { long = false } = {}) {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return escape(value);

    const day = date.getDate();
    const year = date.getFullYear();

    if (long) return digits(`${day}`) + ' ' + MONTHS[date.getMonth()] + ' ' + digits(`${year}`);

    const month = String(date.getMonth() + 1).padStart(2, '0');
    return digits(`${year}-${month}-${String(day).padStart(2, '0')}`);
  }

  function formatNumber(value) {
    if (value === null || value === undefined) return '—';
    return digits(Number(value).toLocaleString('en-US'));
  }

  function age(birthDate) {
    if (!birthDate) return null;
    const birth = new Date(birthDate);
    const now = new Date();
    let years = now.getFullYear() - birth.getFullYear();
    const monthDiff = now.getMonth() - birth.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && now.getDate() < birth.getDate())) years -= 1;
    return years;
  }

  /* ---------------------------------------------------------------------
     الإشعارات
     ------------------------------------------------------------------ */

  function toast(message, type = 'info', duration = 3200) {
    const host = document.getElementById('toasts');
    if (!host) return;

    const element = document.createElement('div');
    element.className = `toast toast--${type}`;
    element.setAttribute('role', type === 'error' ? 'alert' : 'status');
    element.textContent = message;
    host.appendChild(element);

    setTimeout(() => {
      element.style.opacity = '0';
      element.style.transition = 'opacity .25s';
      setTimeout(() => element.remove(), 260);
    }, duration);
  }

  /* ---------------------------------------------------------------------
     بناء العناصر
     ------------------------------------------------------------------ */

  function initials(name) {
    if (!name) return '؟';
    const parts = String(name).trim().split(/\s+/);
    return parts[0].charAt(0);
  }

  function personAvatar(person) {
    const feminine = person.gender === 'أنثى' ? ' avatar--f' : '';
    return `<span class="avatar${feminine}" aria-hidden="true">${escape(initials(person.first_name || person.full_name))}</span>`;
  }

  function lifeBadge(person) {
    if (person.life_status === 'متوفى') {
      return '<span class="badge badge--muted">متوفى</span>';
    }
    if (person.life_status === 'مفقود') {
      return '<span class="badge badge--warning">مفقود</span>';
    }
    return '';
  }

  function personListItem(person, { similarity = null } = {}) {
    const years = age(person.birth_date);
    const score = similarity !== null && similarity !== undefined
      ? `<span class="badge">تطابق ${digits(Math.round(similarity * 100))}٪</span>`
      : '';

    return `
      <a class="list-item" href="#/person/${escape(person.id)}">
        ${personAvatar(person)}
        <span class="list-item__body">
          <span class="list-item__title">${escape(person.full_name)}</span>
          <span class="list-item__meta">
            <span class="num">${escape(digits(person.national_id))}</span>
            ${years !== null ? `<span>${digits(years)} سنة</span>` : ''}
            ${lifeBadge(person)}
            ${score}
          </span>
        </span>
        <span class="list-item__chevron" aria-hidden="true">‹</span>
      </a>`;
  }

  function dataRow(label, value) {
    if (value === null || value === undefined || value === '') return '';
    return `
      <div class="data-row">
        <span class="data-row__label">${escape(label)}</span>
        <span class="data-row__value">${value}</span>
      </div>`;
  }

  function empty(message, icon = '⌕') {
    return `
      <div class="empty">
        <span class="empty__icon" aria-hidden="true">${icon}</span>
        <p>${escape(message)}</p>
      </div>`;
  }

  function skeletons(count = 3) {
    return Array.from({ length: count }, () => '<div class="skeleton"></div>').join('');
  }

  function spinner() {
    return '<div class="loading-row"><div class="spinner spinner--dark" role="status" aria-label="جارٍ التحميل"></div></div>';
  }

  function errorBox(message) {
    return `<div class="alert alert--error" role="alert">${escape(message)}</div>`;
  }

  /* ---------------------------------------------------------------------
     النماذج
     ------------------------------------------------------------------ */

  /** يعرض أخطاء التحقق على الحقول المعنيّة بدل رسالة عامة. */
  function showFieldErrors(form, fields) {
    form.querySelectorAll('[data-error-for]').forEach((node) => { node.textContent = ''; });
    form.querySelectorAll('[aria-invalid]').forEach((node) => {
      node.removeAttribute('aria-invalid');
    });

    (fields || []).forEach((field) => {
      const input = form.querySelector(`[name="${field.name}"]`);
      const slot = form.querySelector(`[data-error-for="${field.name}"]`);
      if (input) input.setAttribute('aria-invalid', 'true');
      if (slot) slot.textContent = field.message;
    });

    const first = form.querySelector('[aria-invalid="true"]');
    if (first) first.focus();
  }

  function formValues(form) {
    const values = {};
    new FormData(form).forEach((value, key) => {
      const trimmed = typeof value === 'string' ? value.trim() : value;
      if (trimmed !== '') values[key] = trimmed;
    });
    return values;
  }

  function setLoading(button, loading, labelWhenIdle) {
    if (!button) return;
    button.disabled = loading;
    button.textContent = loading ? 'جارٍ المعالجة…' : labelWhenIdle;
  }

  return {
    escape,
    digits,
    formatDate,
    formatNumber,
    age,
    toast,
    personAvatar,
    personListItem,
    lifeBadge,
    dataRow,
    empty,
    skeletons,
    spinner,
    errorBox,
    showFieldErrors,
    formValues,
    setLoading,
    initials,
    preferArabicNumerals,
  };
})();
