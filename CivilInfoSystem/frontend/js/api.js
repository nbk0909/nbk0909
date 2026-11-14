/* =============================================================================
   عميل الواجهة البرمجية
   يتولّى الرموز وتجديدها تلقائياً وترجمة الأخطاء إلى رسائل عربية
   ============================================================================= */

const API = (() => {
  'use strict';

  const BASE = (() => {
    // الواجهة والخادم قد يعملان على منفذين مختلفين في التطوير
    const override = localStorage.getItem('api_base');
    if (override) return override;
    if (location.port === '8080' || location.port === '5500') {
      return `${location.protocol}//${location.hostname}:8000/api/v1`;
    }
    return `${location.origin}/api/v1`;
  })();

  const STORAGE = {
    access: 'civil_access',
    refresh: 'civil_refresh',
    user: 'civil_user',
  };

  let refreshPromise = null;   // يمنع تجديدين متزامنين

  /* ---------------------------------------------------------------------
     تخزين الجلسة
     ------------------------------------------------------------------ */

  const session = {
    get access() { return localStorage.getItem(STORAGE.access); },
    get refresh() { return localStorage.getItem(STORAGE.refresh); },

    get user() {
      try { return JSON.parse(localStorage.getItem(STORAGE.user) || 'null'); }
      catch { return null; }
    },

    save(payload) {
      localStorage.setItem(STORAGE.access, payload.access_token);
      localStorage.setItem(STORAGE.refresh, payload.refresh_token);
      localStorage.setItem(STORAGE.user, JSON.stringify(payload.user));
    },

    clear() {
      Object.values(STORAGE).forEach((key) => localStorage.removeItem(key));
    },

    get isAuthenticated() { return Boolean(this.access); },

    can(permission) {
      const user = this.user;
      return Boolean(user && user.permissions && user.permissions.includes(permission));
    },
  };

  /* ---------------------------------------------------------------------
     الأخطاء
     ------------------------------------------------------------------ */

  class ApiError extends Error {
    constructor(message, { status = 0, code = null, fields = [] } = {}) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
      this.code = code;
      this.fields = fields;
    }
  }

  /**
   * يستخرج رسالة عربية مفهومة من جسم الاستجابة.
   * الخادم يُرجع الأخطاء بأشكال ثلاثة: detail نصّي، أو detail كائن،
   * أو قائمة أخطاء تحقّق — فتُوحَّد هنا في مكان واحد.
   */
  function parseError(status, body) {
    if (!body) {
      return new ApiError('تعذّر الاتصال بالخادم', { status });
    }

    // أخطاء التحقق من المدخلات
    if (Array.isArray(body['الأخطاء'])) {
      const fields = body['الأخطاء'].map((e) => ({
        name: e['المعرّف'],
        label: e['الحقل'],
        message: e['الرسالة'],
      }));
      return new ApiError(body['الرسالة'] || 'بيانات غير صالحة', { status, fields });
    }

    const detail = body.detail;
    if (detail && typeof detail === 'object') {
      return new ApiError(detail['الرسالة'] || 'حدث خطأ', {
        status,
        code: detail['الرمز'] || null,
      });
    }

    if (typeof detail === 'string') {
      return new ApiError(detail, { status });
    }

    return new ApiError(body['الرسالة'] || 'حدث خطأ غير متوقّع', { status });
  }

  /* ---------------------------------------------------------------------
     تجديد الرمز
     ------------------------------------------------------------------ */

  async function refreshAccessToken() {
    // التجديد يُبطل الرمز القديم، فطلبان متزامنان يُسقطان الجلسة كلها
    // (يُعدّ الثاني إعادة استعمال لرمز مُبطَل). لذلك يُشارَك وعد واحد.
    if (refreshPromise) return refreshPromise;

    const token = session.refresh;
    if (!token) return Promise.reject(new ApiError('انتهت الجلسة', { status: 401 }));

    refreshPromise = (async () => {
      try {
        const response = await fetch(`${BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: token }),
        });

        if (!response.ok) {
          session.clear();
          throw new ApiError('انتهت الجلسة. سجّل الدخول من جديد', { status: 401 });
        }

        const payload = await response.json();
        session.save(payload);
        return payload.access_token;
      } finally {
        refreshPromise = null;
      }
    })();

    return refreshPromise;
  }

  /* ---------------------------------------------------------------------
     الطلب الأساسي
     ------------------------------------------------------------------ */

  async function request(path, { method = 'GET', body, params, auth = true, retry = true } = {}) {
    let url = `${BASE}${path}`;

    if (params) {
      const query = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          query.append(key, value);
        }
      });
      const queryString = query.toString();
      if (queryString) url += `?${queryString}`;
    }

    const headers = {};
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (auth && session.access) headers.Authorization = `Bearer ${session.access}`;

    let response;
    try {
      response = await fetch(url, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch {
      throw new ApiError(
        navigator.onLine ? 'تعذّر الوصول إلى الخادم' : 'لا يوجد اتصال بالشبكة',
        { status: 0, code: 'network' }
      );
    }

    // الرمز منتهٍ: يُجدَّد مرة واحدة ثم يُعاد الطلب
    if (response.status === 401 && auth && retry && session.refresh) {
      try {
        await refreshAccessToken();
        return request(path, { method, body, params, auth, retry: false });
      } catch (error) {
        session.clear();
        throw error;
      }
    }

    if (response.status === 204) return null;

    let payload = null;
    try { payload = await response.json(); } catch { /* استجابة بلا جسم */ }

    if (!response.ok) throw parseError(response.status, payload);

    return payload;
  }

  /* ---------------------------------------------------------------------
     الواجهات
     ------------------------------------------------------------------ */

  return {
    BASE,
    session,
    ApiError,
    request,

    // المصادقة
    async login(username, password, totpCode) {
      const payload = await request('/auth/login', {
        method: 'POST',
        auth: false,
        body: {
          username,
          password,
          totp_code: totpCode || null,
        },
      });
      session.save(payload);
      return payload;
    },

    async logout() {
      try {
        await request('/auth/logout', {
          method: 'POST',
          body: { refresh_token: session.refresh },
        });
      } catch { /* الخروج محلياً يتمّ على أي حال */ }
      session.clear();
    },

    me: () => request('/auth/me'),

    changePassword: (current, next) =>
      request('/auth/change-password', {
        method: 'POST',
        body: { current_password: current, new_password: next },
      }),

    // الأشخاص
    searchPersons: (params) => request('/persons/search', { params }),
    suggestNames: (prefix) => request('/persons/suggest', { params: { prefix } }),
    getPerson: (id) => request(`/persons/${id}`),
    getPersonByNationalId: (nid) => request(`/persons/by-national-id/${nid}`),
    createPerson: (data) => request('/persons', { method: 'POST', body: data }),
    updatePerson: (id, data) => request(`/persons/${id}`, { method: 'PATCH', body: data }),
    getFamilyTree: (id) => request(`/persons/${id}/family-tree`),
    getRelations: (id) => request(`/persons/${id}/relations`),
    checkConsistency: (id) => request(`/persons/${id}/consistency`),
    getAddresses: (id) => request(`/persons/${id}/addresses`),
    getPersonDocuments: (id) => request(`/persons/${id}/documents`),

    // الواقعات
    listBirths: (params) => request('/births', { params }),
    registerBirth: (data) => request('/births', { method: 'POST', body: data }),
    listDeaths: (params) => request('/deaths', { params }),
    registerDeath: (data) => request('/deaths', { method: 'POST', body: data }),
    listMarriages: (params) => request('/marriages', { params }),

    // الوثائق والمعاملات
    expiringDocuments: (days) => request('/documents/expiring', { params: { days } }),
    listRequests: (params) => request('/requests', { params }),
    createRequest: (data) => request('/requests', { method: 'POST', body: data }),
    decideRequest: (id, data) =>
      request(`/requests/${id}/decision`, { method: 'PATCH', body: data }),

    // التقسيمات الإدارية
    governorates: () => request('/locations/governorates', { params: { with_districts: true } }),
  };
})();
