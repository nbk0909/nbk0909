/* =============================================================================
   التوجيه وإقلاع التطبيق
   ============================================================================= */

const App = (() => {
  'use strict';

  const elements = {};

  /* ---------------------------------------------------------------------
     المسارات
     ------------------------------------------------------------------ */

  const routes = [
    { pattern: /^\/$/, title: 'الرئيسية', tab: '/', render: (c) => DashboardView.render(c) },
    { pattern: /^\/search$/, title: 'البحث', tab: '/search', render: (c) => SearchView.render(c) },
    { pattern: /^\/person\/new$/, title: 'تسجيل شخص', tab: '/person/new', render: (c) => PersonView.renderForm(c) },
    { pattern: /^\/person\/([^/]+)\/tree$/, title: 'شجرة العائلة', back: true, render: (c, m) => PersonView.renderTree(c, m[1]) },
    { pattern: /^\/person\/([^/]+)$/, title: 'السجل المدني', back: true, render: (c, m) => PersonView.renderDetail(c, m[1]) },
    { pattern: /^\/births$/, title: 'واقعات الميلاد', back: true, render: (c) => RecordsView.births(c) },
    { pattern: /^\/deaths$/, title: 'واقعات الوفاة', back: true, render: (c) => RecordsView.deaths(c) },
    { pattern: /^\/marriages$/, title: 'عقود الزواج', back: true, render: (c) => RecordsView.marriages(c) },
    { pattern: /^\/documents\/expiring$/, title: 'وثائق توشك على الانتهاء', back: true, render: (c) => RecordsView.expiringDocuments(c) },
    { pattern: /^\/requests$/, title: 'المعاملات', tab: '/requests', render: (c) => RecordsView.requests(c) },
    { pattern: /^\/settings$/, title: 'الإعدادات', back: true, render: (c) => RecordsView.settings(c) },
  ];

  function currentRoute() {
    const path = (location.hash || '#/').slice(1) || '/';
    for (const route of routes) {
      const match = path.match(route.pattern);
      if (match) return { route, match, path };
    }
    return { route: null, match: null, path };
  }

  async function navigate() {
    if (!API.session.isAuthenticated) {
      showLogin();
      return;
    }

    const { route, match } = currentRoute();

    if (!route) {
      elements.content.innerHTML = UI.empty('الصفحة غير موجودة', '⚠');
      setTitle('غير موجود');
      return;
    }

    setTitle(route.title);
    elements.back.hidden = !route.back;
    highlightTab(route.tab);

    // كل انتقال يبدأ من أعلى الصفحة، ويُنقل التركيز للمحتوى لقارئات الشاشة
    window.scrollTo(0, 0);
    elements.content.innerHTML = '';

    try {
      await route.render(elements.content, match);
    } catch (error) {
      elements.content.innerHTML = UI.errorBox(error.message || 'حدث خطأ في عرض الصفحة');
    }

    elements.content.focus({ preventScroll: true });
  }

  function setTitle(title) {
    elements.title.textContent = title;
    document.title = `${title} — نظام المعلومات المدنية`;
  }

  function highlightTab(tab) {
    document.querySelectorAll('.tabbar__item').forEach((item) => {
      if (tab && item.dataset.tab === tab) {
        item.setAttribute('aria-current', 'page');
      } else {
        item.removeAttribute('aria-current');
      }
    });
  }

  /* ---------------------------------------------------------------------
     الدخول والخروج
     ------------------------------------------------------------------ */

  function showLogin() {
    elements.app.hidden = true;
    elements.login.hidden = false;
    elements.splash.hidden = true;

    // إعادة النموذج إلى حالته الابتدائية.
    // بدون ذلك يبقى الزر معطّلاً بنص «جارٍ المعالجة…» من محاولة الدخول
    // الناجحة السابقة، فيتعذّر على المستخدم الدخول ثانيةً بعد الخروج أو
    // بعد تغيير كلمة مروره إلا بإعادة تحميل الصفحة.
    const form = document.getElementById('login-form');
    if (form) {
      form.reset();
      UI.setLoading(form.querySelector('button[type="submit"]'), false, 'دخول');
      document.getElementById('login-error').hidden = true;
      document.getElementById('totp-field').hidden = true;
    }
  }

  function showApp() {
    elements.login.hidden = true;
    elements.app.hidden = false;
    elements.splash.hidden = true;
    fillMenu();
  }

  function fillMenu() {
    const user = API.session.user || {};
    elements.menuName.textContent = user.full_name_ar || '';
    elements.menuRole.textContent = (user.roles || []).map((r) => r.name_ar).join('، ');
    elements.menuAvatar.textContent = UI.initials(user.full_name_ar);
  }

  function forceLogout() {
    API.session.clear();
    closeSheet();
    showLogin();
    location.hash = '#/';
  }

  async function handleLogin(event) {
    event.preventDefault();

    const form = event.target;
    const button = form.querySelector('button[type="submit"]');
    const errorBox = document.getElementById('login-error');
    const totpField = document.getElementById('totp-field');
    errorBox.hidden = true;

    const values = UI.formValues(form);
    UI.setLoading(button, true, 'دخول');

    try {
      await API.login(values.username, values.password, values.totp_code);

      const user = API.session.user;
      showApp();

      if (user && user.must_change_password) {
        UI.toast('يجب تغيير كلمة المرور قبل استخدام النظام', 'error', 5000);
        location.hash = '#/settings';
      } else {
        location.hash = '#/';
      }
      await navigate();
    } catch (error) {
      // المصادقة الثنائية مطلوبة: يُكشف الحقل بدل عرضه دائماً
      if (error.code === 'totp_required') {
        totpField.hidden = false;
        totpField.querySelector('input').focus();
        errorBox.textContent = 'أدخل رمز المصادقة الثنائية';
      } else {
        errorBox.textContent = error.message;
      }
      errorBox.hidden = false;
      UI.setLoading(button, false, 'دخول');
    }
  }

  /* ---------------------------------------------------------------------
     القائمة المنسدلة
     ------------------------------------------------------------------ */

  function openSheet() {
    elements.sheet.hidden = false;
    elements.menuButton.setAttribute('aria-expanded', 'true');
  }

  function closeSheet() {
    elements.sheet.hidden = true;
    elements.menuButton.setAttribute('aria-expanded', 'false');
  }

  /* ---------------------------------------------------------------------
     حالة الاتصال
     ------------------------------------------------------------------ */

  function updateOnlineStatus() {
    elements.offlineBar.hidden = navigator.onLine;
  }

  /* ---------------------------------------------------------------------
     الإقلاع
     ------------------------------------------------------------------ */

  async function boot() {
    Object.assign(elements, {
      splash: document.getElementById('splash'),
      login: document.getElementById('view-login'),
      app: document.getElementById('app'),
      content: document.getElementById('content'),
      title: document.getElementById('page-title'),
      back: document.getElementById('btn-back'),
      menuButton: document.getElementById('btn-menu'),
      sheet: document.getElementById('menu-sheet'),
      menuName: document.getElementById('menu-name'),
      menuRole: document.getElementById('menu-role'),
      menuAvatar: document.getElementById('menu-avatar'),
      offlineBar: document.getElementById('offline-bar'),
    });

    // الأحداث
    document.getElementById('login-form').addEventListener('submit', handleLogin);
    elements.back.addEventListener('click', () => history.back());
    elements.menuButton.addEventListener('click', openSheet);
    document.getElementById('btn-logout').addEventListener('click', async () => {
      await API.logout();
      forceLogout();
    });

    document.addEventListener('click', (event) => {
      if (event.target.closest('[data-close-sheet]')) closeSheet();
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !elements.sheet.hidden) closeSheet();
    });

    document.querySelector('[data-toggle-password]').addEventListener('click', (event) => {
      const input = event.target.closest('.field__wrap').querySelector('input');
      const isPassword = input.type === 'password';
      input.type = isPassword ? 'text' : 'password';
      event.target.setAttribute(
        'aria-label',
        isPassword ? 'إخفاء كلمة المرور' : 'إظهار كلمة المرور'
      );
    });

    window.addEventListener('hashchange', navigate);
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    updateOnlineStatus();

    // التحقق من صلاحية الجلسة المحفوظة قبل عرض التطبيق
    if (API.session.isAuthenticated) {
      try {
        const user = await API.me();
        localStorage.setItem('civil_user', JSON.stringify(user));
        showApp();
        await navigate();
      } catch {
        API.session.clear();
        showLogin();
      }
    } else {
      showLogin();
    }

    registerServiceWorker();
  }

  function registerServiceWorker() {
    if (!('serviceWorker' in navigator)) return;
    // الملف يُسجَّل من جذر الواجهة ليتحكّم بكل مساراتها
    navigator.serviceWorker.register('service-worker.js').catch(() => {
      // فشل التسجيل لا يمنع عمل التطبيق، يمنع العمل دون اتصال فقط
    });
  }

  return { boot, navigate, setTitle, forceLogout, closeSheet };
})();

document.addEventListener('DOMContentLoaded', () => App.boot());
