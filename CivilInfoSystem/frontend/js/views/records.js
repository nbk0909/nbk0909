/* =============================================================================
   شاشات الواقعات والوثائق والمعاملات والإعدادات
   ============================================================================= */

const RecordsView = (() => {
  'use strict';

  /** قالب مشترك لقوائم السجلات: تحميل، ثم عرض أو حالة فارغة أو خطأ. */
  async function listPage(container, { title, load, item, emptyText, icon }) {
    App.setTitle(title);
    container.innerHTML = `<div id="records-host">${UI.skeletons(4)}</div>`;
    const host = container.querySelector('#records-host');

    try {
      const page = await load();
      const items = page.items || page;

      if (!items.length) {
        host.innerHTML = UI.empty(emptyText, icon);
        return;
      }

      const total = page.total !== undefined ? page.total : items.length;
      host.innerHTML = `
        <p style="font-size:.85rem;color:var(--text-muted);margin:0 0 .6rem">
          ${UI.digits(total)} سجل
        </p>
        <div class="list">${items.map(item).join('')}</div>`;
    } catch (error) {
      host.innerHTML = UI.errorBox(error.message);
    }
  }

  /* ---------------------------------------------------------------------
     واقعات الميلاد
     ------------------------------------------------------------------ */

  function births(container) {
    return listPage(container, {
      title: 'واقعات الميلاد',
      icon: '☺',
      emptyText: 'لا توجد واقعات ميلاد مسجّلة',
      load: () => API.listBirths({ page_size: 30 }),
      item: (record) => `
        <a class="list-item" href="#/person/${UI.escape(record.person.id)}">
          ${UI.personAvatar(record.person)}
          <span class="list-item__body">
            <span class="list-item__title">${UI.escape(record.person.full_name)}</span>
            <span class="list-item__meta">
              <span class="num">${UI.escape(UI.digits(record.record_number))}</span>
              <span class="num">${UI.formatDate(record.birth_date)}</span>
              ${record.hospital_name ? `<span>${UI.escape(record.hospital_name)}</span>` : ''}
            </span>
          </span>
          <span class="list-item__chevron" aria-hidden="true">‹</span>
        </a>`,
    });
  }

  /* ---------------------------------------------------------------------
     واقعات الوفاة
     ------------------------------------------------------------------ */

  function deaths(container) {
    return listPage(container, {
      title: 'واقعات الوفاة',
      icon: '☖',
      emptyText: 'لا توجد واقعات وفاة مسجّلة',
      load: () => API.listDeaths({ page_size: 30 }),
      item: (record) => `
        <a class="list-item" href="#/person/${UI.escape(record.person.id)}">
          ${UI.personAvatar(record.person)}
          <span class="list-item__body">
            <span class="list-item__title">${UI.escape(record.person.full_name)}</span>
            <span class="list-item__meta">
              <span class="num">${UI.escape(UI.digits(record.record_number))}</span>
              <span class="num">${UI.formatDate(record.death_date)}</span>
              ${record.cause_of_death ? `<span>${UI.escape(record.cause_of_death)}</span>` : ''}
            </span>
          </span>
          <span class="list-item__chevron" aria-hidden="true">‹</span>
        </a>`,
    });
  }

  /* ---------------------------------------------------------------------
     عقود الزواج
     ------------------------------------------------------------------ */

  function marriages(container) {
    return listPage(container, {
      title: 'عقود الزواج',
      icon: '⚭',
      emptyText: 'لا توجد عقود زواج مسجّلة',
      load: () => API.listMarriages({ page_size: 30 }),
      item: (contract) => `
        <div class="list-item">
          <span class="list-item__body">
            <span class="list-item__title">
              ${UI.escape(contract.husband.full_name)} &amp; ${UI.escape(contract.wife.full_name)}
            </span>
            <span class="list-item__meta">
              <span class="num">${UI.escape(UI.digits(contract.contract_number))}</span>
              <span class="num">${UI.formatDate(contract.contract_date)}</span>
              ${contract.is_active
                ? '<span class="badge badge--success">نشط</span>'
                : '<span class="badge badge--muted">منتهٍ</span>'}
            </span>
          </span>
        </div>`,
    });
  }

  /* ---------------------------------------------------------------------
     الوثائق التي توشك على الانتهاء
     ------------------------------------------------------------------ */

  function expiringDocuments(container) {
    return listPage(container, {
      title: 'وثائق توشك على الانتهاء',
      icon: '▤',
      emptyText: 'لا توجد وثائق تنتهي خلال 90 يوماً',
      load: () => API.expiringDocuments(90),
      item: (doc) => `
        <a class="list-item" href="#/person/${UI.escape(doc.person.id)}">
          ${UI.personAvatar(doc.person)}
          <span class="list-item__body">
            <span class="list-item__title">${UI.escape(doc.person.full_name)}</span>
            <span class="list-item__meta">
              <span>${UI.escape(doc.document_type)}</span>
              <span class="num">${UI.escape(UI.digits(doc.document_number))}</span>
              <span class="badge badge--warning">
                ${UI.digits(doc.days_until_expiry)} يوماً
              </span>
            </span>
          </span>
          <span class="list-item__chevron" aria-hidden="true">‹</span>
        </a>`,
    });
  }

  /* ---------------------------------------------------------------------
     المعاملات
     ------------------------------------------------------------------ */

  function requests(container) {
    return listPage(container, {
      title: 'المعاملات',
      icon: '☰',
      emptyText: 'لا توجد معاملات',
      load: () => API.listRequests({ page_size: 30 }),
      item: (request) => {
        const badges = {
          'مقبول': 'badge--success',
          'مرفوض': 'badge--danger',
          'قيد المراجعة': 'badge--warning',
          'ملغى': 'badge--muted',
        };
        return `
          <div class="list-item">
            <span class="list-item__body">
              <span class="list-item__title">${UI.escape(request.subject)}</span>
              <span class="list-item__meta">
                <span class="num">${UI.escape(UI.digits(request.reference_number))}</span>
                <span>${UI.escape(request.person.full_name)}</span>
                <span class="badge ${badges[request.status] || ''}">${UI.escape(request.status)}</span>
              </span>
            </span>
          </div>`;
      },
    });
  }

  /* ---------------------------------------------------------------------
     الإعدادات
     ------------------------------------------------------------------ */

  function settings(container) {
    App.setTitle('الإعدادات');
    const user = API.session.user || {};
    const arabicNumerals = UI.preferArabicNumerals();

    container.innerHTML = `
      <section class="card">
        <h3 class="card__title">الحساب</h3>
        <div class="data-list">
          ${UI.dataRow('الاسم', UI.escape(user.full_name_ar))}
          ${UI.dataRow('اسم المستخدم', `<span class="num">${UI.escape(user.username)}</span>`)}
          ${UI.dataRow('الأدوار', UI.escape((user.roles || []).map((r) => r.name_ar).join('، ')))}
          ${UI.dataRow('عدد الصلاحيات', UI.digits((user.permissions || []).length))}
          ${UI.dataRow('المصادقة الثنائية',
            user.totp_enabled
              ? '<span class="badge badge--success">مفعّلة</span>'
              : '<span class="badge badge--warning">غير مفعّلة</span>')}
        </div>
      </section>

      <section class="card">
        <h3 class="card__title">العرض</h3>
        <label class="field" style="margin:0">
          <span class="field__label">شكل الأرقام</span>
          <select class="field__select" id="numerals-select">
            <option value="latin" ${!arabicNumerals ? 'selected' : ''}>لاتينية (1234)</option>
            <option value="arabic" ${arabicNumerals ? 'selected' : ''}>عربية (١٢٣٤)</option>
          </select>
        </label>
      </section>

      <section class="card">
        <h3 class="card__title">تغيير كلمة المرور</h3>
        <form id="password-form" novalidate>
          <div id="password-error" class="alert alert--error" hidden role="alert"></div>

          <label class="field">
            <span class="field__label">كلمة المرور الحالية</span>
            <input class="field__input" type="password" name="current_password"
                   autocomplete="current-password" required dir="ltr">
          </label>

          <label class="field">
            <span class="field__label">كلمة المرور الجديدة</span>
            <input class="field__input" type="password" name="new_password"
                   autocomplete="new-password" required minlength="10" dir="ltr">
            <span class="field__hint">
              10 أحرف على الأقل، وتشمل حرفاً كبيراً وصغيراً ورقماً ورمزاً
            </span>
            <span class="field__error" data-error-for="new_password"></span>
          </label>

          <button type="submit" class="btn btn--primary btn--block">تغيير كلمة المرور</button>
        </form>
      </section>`;

    container.querySelector('#numerals-select').addEventListener('change', (event) => {
      localStorage.setItem('numerals', event.target.value);
      UI.toast('تم حفظ التفضيل', 'success');
    });

    const form = container.querySelector('#password-form');
    form.addEventListener('submit', async (event) => {
      event.preventDefault();

      const button = form.querySelector('button[type="submit"]');
      const errorBox = form.querySelector('#password-error');
      errorBox.hidden = true;

      const values = UI.formValues(form);
      UI.setLoading(button, true, 'تغيير كلمة المرور');

      try {
        await API.changePassword(values.current_password, values.new_password);
        UI.toast('تم تغيير كلمة المرور. سجّل الدخول من جديد', 'success');
        setTimeout(() => App.forceLogout(), 1400);
      } catch (error) {
        if (error.fields && error.fields.length) {
          UI.showFieldErrors(form, error.fields);
        }
        errorBox.textContent = error.message;
        errorBox.hidden = false;
        UI.setLoading(button, false, 'تغيير كلمة المرور');
      }
    });
  }

  return {
    births,
    deaths,
    marriages,
    expiringDocuments,
    requests,
    settings,
  };
})();
