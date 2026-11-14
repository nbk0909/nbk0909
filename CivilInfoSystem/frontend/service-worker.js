/* =============================================================================
   عامل الخدمة — يتيح تثبيت التطبيق وتشغيله جزئياً دون اتصال
   ============================================================================= */

// أي تعديل على ملفات القشرة يستوجب رفع رقم النسخة، وإلا بقيت النسخة
// القديمة مخزّنة في أجهزة المستخدمين
const VERSION = 'civil-v1';
const SHELL_CACHE = `${VERSION}-shell`;
const DATA_CACHE = `${VERSION}-data`;

// قشرة التطبيق: كل ما يلزم لعرض واجهة عاملة دون شبكة
const SHELL = [
  './',
  './index.html',
  './manifest.json',
  './css/app.css',
  './js/api.js',
  './js/ui.js',
  './js/app.js',
  './js/views/dashboard.js',
  './js/views/search.js',
  './js/views/person.js',
  './js/views/records.js',
  './assets/icons/icon-180.png',
  './assets/icons/icon-192.png',
  './assets/icons/favicon.png',
];

/* ---------------------------------------------------------------------------
   التثبيت والتفعيل
   ------------------------------------------------------------------------ */

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      // addAll ترفض الدفعة كلها إن فشل ملف واحد، فتُضاف الملفات فرادى
      // ليبقى ما نجح منها محفوظاً
      .then((cache) => Promise.allSettled(SHELL.map((url) => cache.add(url))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => !key.startsWith(VERSION))
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

/* ---------------------------------------------------------------------------
   الاعتراض
   ------------------------------------------------------------------------ */

self.addEventListener('fetch', (event) => {
  const { request } = event;

  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin && !url.pathname.startsWith('/api/')) {
    return;
  }

  // نداءات الواجهة البرمجية: الشبكة أولاً — البيانات المدنية يجب أن تكون
  // حديثة، والنسخة المخزّنة احتياط عند انقطاع الاتصال فقط.
  if (url.pathname.includes('/api/')) {
    event.respondWith(networkFirst(request));
    return;
  }

  // ملفات القشرة: الذاكرة أولاً — لا تتغيّر إلا بتغيّر رقم النسخة
  event.respondWith(cacheFirst(request));
});

async function networkFirst(request) {
  try {
    const response = await fetch(request);

    // لا تُخزَّن إلا الاستجابات الناجحة: تخزين 401 أو 500 يعني إعادة
    // عرض الخطأ للمستخدم بعد عودة الشبكة
    if (response.ok) {
      const cache = await caches.open(DATA_CACHE);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) return cached;

    return new Response(
      JSON.stringify({
        نجاح: false,
        الرسالة: 'لا يوجد اتصال بالشبكة ولا نسخة محفوظة من هذه البيانات',
      }),
      { status: 503, headers: { 'Content-Type': 'application/json; charset=utf-8' } }
    );
  }
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(SHELL_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    // التنقّل دون اتصال يُعاد إلى القشرة، فيعمل التوجيه الداخلي
    if (request.mode === 'navigate') {
      const shell = await caches.match('./index.html');
      if (shell) return shell;
    }
    throw error;
  }
}
