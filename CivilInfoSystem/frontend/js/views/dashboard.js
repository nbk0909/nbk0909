/* =============================================================================
   الشاشة الرئيسية
   ============================================================================= */

const DashboardView = (() => {
  'use strict';

  async function render(container) {
    const user = API.session.user || {};

    container.innerHTML = `
      <section class="card" style="background:var(--primary);color:#fff;border:0">
        <p style="margin:0;font-size:.85rem;opacity:.85">أهلاً بك</p>
        <h2 style="margin:.15rem 0 0;color:#fff">${UI.escape(user.full_name_ar || '')}</h2>
        <p style="margin:.35rem 0 0;font-size:.82rem;opacity:.85">
          ${UI.escape((user.roles || []).map((r) => r.name_ar).join('، '))}
        </p>
      </section>

      <div class="stat-grid" id="dash-stats">
        ${['السكان', 'المواليد', 'الوفيات', 'المعاملات'].map((label) => `
          <div class="stat">
            <div class="stat__value" data-loading>—</div>
            <div class="stat__label">${label}</div>
          </div>`).join('')}
      </div>

      <section class="card">
        <h3 class="card__title">إجراءات سريعة</h3>
        <div style="display:grid;gap:.5rem">
          <a class="btn btn--ghost btn--block" href="#/search">البحث في السجل المدني</a>
          ${API.session.can('persons.create')
            ? '<a class="btn btn--ghost btn--block" href="#/person/new">تسجيل شخص جديد</a>' : ''}
          <a class="btn btn--ghost btn--block" href="#/documents/expiring">وثائق توشك على الانتهاء</a>
        </div>
      </section>

      <section class="card">
        <h3 class="card__title">أحدث المعاملات</h3>
        <div id="dash-requests">${UI.skeletons(2)}</div>
      </section>`;

    loadStats(container);
    loadRequests(container);
  }

  async function loadStats(container) {
    const cells = container.querySelectorAll('#dash-stats .stat__value');

    // الطلبات متوازية: الشاشة تعرض ما يصل أولاً بدل انتظار الأبطأ
    const results = await Promise.allSettled([
      API.searchPersons({ life_status: 'حي', page_size: 1 }),
      API.listBirths({ page_size: 1 }),
      API.listDeaths({ page_size: 1 }),
      API.listRequests({ page_size: 1 }),
    ]);

    results.forEach((result, index) => {
      const cell = cells[index];
      if (!cell) return;
      cell.textContent = result.status === 'fulfilled'
        ? UI.formatNumber(result.value.total)
        : '—';
    });
  }

  async function loadRequests(container) {
    const host = container.querySelector('#dash-requests');
    if (!host) return;

    try {
      const page = await API.listRequests({ page_size: 5 });

      if (!page.items.length) {
        host.innerHTML = UI.empty('لا توجد معاملات', '☰');
        return;
      }

      host.innerHTML = `<div class="list">${page.items.map(requestItem).join('')}</div>`;
    } catch (error) {
      host.innerHTML = UI.errorBox(error.message);
    }
  }

  const STATUS_BADGE = {
    'مقبول': 'badge--success',
    'مرفوض': 'badge--danger',
    'قيد المراجعة': 'badge--warning',
    'ملغى': 'badge--muted',
  };

  function requestItem(request) {
    const badgeClass = STATUS_BADGE[request.status] || '';
    return `
      <div class="list-item">
        <span class="list-item__body">
          <span class="list-item__title">${UI.escape(request.subject)}</span>
          <span class="list-item__meta">
            <span class="num">${UI.escape(UI.digits(request.reference_number))}</span>
            <span class="badge ${badgeClass}">${UI.escape(request.status)}</span>
          </span>
        </span>
      </div>`;
  }

  return { render, requestItem };
})();
