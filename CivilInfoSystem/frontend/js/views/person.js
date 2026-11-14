/* =============================================================================
   شاشة تفاصيل الشخص وشجرة العائلة وتسجيل شخص جديد
   ============================================================================= */

const PersonView = (() => {
  'use strict';

  /* ---------------------------------------------------------------------
     تفاصيل الشخص
     ------------------------------------------------------------------ */

  async function renderDetail(container, personId) {
    container.innerHTML = UI.spinner();

    let person;
    try {
      person = await API.getPerson(personId);
    } catch (error) {
      container.innerHTML = UI.errorBox(error.message);
      return;
    }

    App.setTitle(person.full_name);

    const years = UI.age(person.birth_date);
    const address = person.current_address;

    container.innerHTML = `
      <section class="card">
        <div style="display:flex;align-items:center;gap:.85rem;margin-bottom:.9rem">
          ${UI.personAvatar(person)}
          <div style="min-width:0">
            <h2 style="margin:0;font-size:1.05rem">${UI.escape(person.full_name)}</h2>
            <p style="margin:.15rem 0 0;font-size:.85rem;color:var(--text-muted)">
              <span class="num">${UI.escape(UI.digits(person.national_id))}</span>
              ${UI.lifeBadge(person)}
            </p>
          </div>
        </div>

        <div class="data-list">
          ${UI.dataRow('تاريخ الميلاد', `<span class="num">${UI.formatDate(person.birth_date, { long: true })}</span>`)}
          ${UI.dataRow('العمر', years !== null ? `${UI.digits(years)} سنة` : null)}
          ${UI.dataRow('الجنس', UI.escape(person.gender))}
          ${UI.dataRow('الحالة الاجتماعية', UI.escape(person.marital_status))}
          ${UI.dataRow('اسم الأم', UI.escape(person.mother_full_name))}
          ${UI.dataRow('الجنسية', UI.escape(person.nationality))}
          ${UI.dataRow('الديانة', UI.escape(person.religion))}
          ${UI.dataRow('فصيلة الدم', person.blood_type ? `<span class="num">${UI.escape(person.blood_type)}</span>` : null)}
          ${UI.dataRow('المهنة', UI.escape(person.occupation))}
          ${UI.dataRow('المؤهل العلمي', UI.escape(person.education_level))}
          ${UI.dataRow('العنوان الحالي', address ? UI.escape(address.formatted) : null)}
        </div>
      </section>

      <section class="card">
        <h3 class="card__title">
          شجرة العائلة
          <a class="btn btn--ghost btn--sm" href="#/person/${UI.escape(personId)}/tree">عرض كامل</a>
        </h3>
        <div id="tree-preview">${UI.skeletons(2)}</div>
      </section>

      <section class="card">
        <h3 class="card__title">الوثائق</h3>
        <div id="person-docs">${UI.skeletons(1)}</div>
      </section>

      <section class="card">
        <h3 class="card__title">فحص تماسك السجل</h3>
        <div id="consistency">${UI.spinner()}</div>
      </section>`;

    loadTreePreview(container, personId);
    loadDocuments(container, personId);
    loadConsistency(container, personId);
  }

  async function loadTreePreview(container, personId) {
    const host = container.querySelector('#tree-preview');
    if (!host) return;

    try {
      const tree = await API.getFamilyTree(personId);
      const close = [];

      if (tree.father) close.push({ node: tree.father, label: 'الأب' });
      if (tree.mother) close.push({ node: tree.mother, label: 'الأم' });
      tree.spouses.forEach((s) => close.push({ node: s, label: s.relation }));
      tree.children.slice(0, 4).forEach((c) => close.push({ node: c, label: c.relation }));

      if (!close.length) {
        host.innerHTML = UI.empty('لا توجد علاقات مسجّلة', '⚯');
        return;
      }

      host.innerHTML = `<div class="tree__row">${close.map((entry) => nodeCard(entry.node, entry.label)).join('')}</div>`;
    } catch (error) {
      host.innerHTML = UI.errorBox(error.message);
    }
  }

  async function loadDocuments(container, personId) {
    const host = container.querySelector('#person-docs');
    if (!host) return;

    try {
      const documents = await API.getPersonDocuments(personId);

      if (!documents.length) {
        host.innerHTML = UI.empty('لا توجد وثائق مسجّلة', '▤');
        return;
      }

      host.innerHTML = `<div class="list">${documents.map(documentItem).join('')}</div>`;
    } catch (error) {
      host.innerHTML = UI.errorBox(error.message);
    }
  }

  function documentItem(doc) {
    let badge = '<span class="badge badge--success">سارية</span>';
    if (doc.status !== 'سارية') {
      badge = `<span class="badge badge--muted">${UI.escape(doc.status)}</span>`;
    } else if (doc.is_expired) {
      badge = '<span class="badge badge--danger">منتهية</span>';
    } else if (doc.days_until_expiry !== null && doc.days_until_expiry <= 90) {
      badge = `<span class="badge badge--warning">تنتهي خلال ${UI.digits(doc.days_until_expiry)} يوماً</span>`;
    }

    return `
      <div class="list-item">
        <span class="list-item__body">
          <span class="list-item__title">${UI.escape(doc.document_type)}</span>
          <span class="list-item__meta">
            <span class="num">${UI.escape(UI.digits(doc.document_number))}</span>
            ${badge}
          </span>
        </span>
      </div>`;
  }

  async function loadConsistency(container, personId) {
    const host = container.querySelector('#consistency');
    if (!host) return;

    try {
      const report = await API.checkConsistency(personId);

      if (report['سليم']) {
        host.innerHTML = '<div class="alert alert--success">لا توجد تعارضات منطقية في السجل</div>';
        return;
      }

      host.innerHTML = `
        <div class="alert alert--warning">
          ${UI.digits(report['عدد_التعارضات'])} تعارض يحتاج مراجعة
        </div>
        <div class="list">
          ${report['التعارضات'].map((conflict) => `
            <div class="list-item">
              <span class="list-item__body">
                <span class="list-item__title">${UI.escape(conflict['نوع_التعارض'])}</span>
                <span class="list-item__meta">${UI.escape(conflict['الوصف'])}</span>
              </span>
            </div>`).join('')}
        </div>`;
    } catch (error) {
      host.innerHTML = UI.errorBox(error.message);
    }
  }

  /* ---------------------------------------------------------------------
     شجرة العائلة الكاملة
     ------------------------------------------------------------------ */

  function nodeCard(node, label) {
    const person = node.person;
    return `
      <a class="tree-node" href="#/person/${UI.escape(person.id)}">
        ${UI.personAvatar(person)}
        <span style="min-width:0">
          <span class="tree-node__name">${UI.escape(person.full_name)}</span>
          <span class="tree-node__rel">${UI.escape(label || node.relation || '')}</span>
        </span>
      </a>`;
  }

  function level(title, nodes) {
    if (!nodes || !nodes.length) return '';
    return `
      <div class="tree__level">
        <h3 class="tree__level-title">${UI.escape(title)}</h3>
        <div class="tree__row">${nodes.map((n) => nodeCard(n)).join('')}</div>
      </div>`;
  }

  async function renderTree(container, personId) {
    container.innerHTML = UI.spinner();

    try {
      const tree = await API.getFamilyTree(personId);
      App.setTitle('شجرة العائلة');

      const parents = [tree.father, tree.mother].filter(Boolean);

      container.innerHTML = `
        <div class="tree">
          ${level('الأجداد', tree.grandparents)}
          ${level('الوالدان', parents)}

          <div class="tree__level">
            <h3 class="tree__level-title">الشخص</h3>
            <div class="tree__row">
              <span class="tree-node tree-node--self">
                ${UI.personAvatar(tree.person)}
                <span style="min-width:0">
                  <span class="tree-node__name">${UI.escape(tree.person.full_name)}</span>
                  <span class="tree-node__rel num">${UI.escape(UI.digits(tree.person.national_id))}</span>
                </span>
              </span>
            </div>
          </div>

          ${level('الإخوة والأخوات', tree.siblings)}
          ${level('الأزواج', tree.spouses)}
          ${level('الأبناء', tree.children)}
          ${level('الأحفاد', tree.grandchildren)}
        </div>`;
    } catch (error) {
      container.innerHTML = UI.errorBox(error.message);
    }
  }

  /* ---------------------------------------------------------------------
     تسجيل شخص جديد
     ------------------------------------------------------------------ */

  async function renderForm(container) {
    if (!API.session.can('persons.create')) {
      container.innerHTML = UI.errorBox('ليست لديك صلاحية تسجيل الأشخاص');
      return;
    }

    container.innerHTML = `
      <form id="person-form" class="card" novalidate>
        <div id="form-error" class="alert alert--error" hidden role="alert"></div>

        <label class="field">
          <span class="field__label">الرقم الوطني</span>
          <input class="field__input num" type="text" name="national_id" required
                 inputmode="numeric" maxlength="12" dir="ltr" autocomplete="off">
          <span class="field__hint">12 خانة رقمية بخانة تدقيق صحيحة</span>
          <span class="field__error" data-error-for="national_id"></span>
        </label>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:.6rem">
          <label class="field">
            <span class="field__label">الاسم الأول</span>
            <input class="field__input" type="text" name="first_name" required minlength="2">
            <span class="field__error" data-error-for="first_name"></span>
          </label>
          <label class="field">
            <span class="field__label">اسم الأب</span>
            <input class="field__input" type="text" name="father_name" required minlength="2">
            <span class="field__error" data-error-for="father_name"></span>
          </label>
          <label class="field">
            <span class="field__label">اسم الجد</span>
            <input class="field__input" type="text" name="grandfather_name" required minlength="2">
            <span class="field__error" data-error-for="grandfather_name"></span>
          </label>
          <label class="field">
            <span class="field__label">اللقب</span>
            <input class="field__input" type="text" name="family_name" required minlength="2">
            <span class="field__error" data-error-for="family_name"></span>
          </label>
        </div>

        <label class="field">
          <span class="field__label">اسم الأم الكامل</span>
          <input class="field__input" type="text" name="mother_full_name" required minlength="2">
          <span class="field__error" data-error-for="mother_full_name"></span>
        </label>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:.6rem">
          <label class="field">
            <span class="field__label">تاريخ الميلاد</span>
            <input class="field__input" type="date" name="birth_date" required>
            <span class="field__error" data-error-for="birth_date"></span>
          </label>
          <label class="field">
            <span class="field__label">الجنس</span>
            <select class="field__select" name="gender" required>
              <option value="">اختر…</option>
              <option value="ذكر">ذكر</option>
              <option value="أنثى">أنثى</option>
            </select>
            <span class="field__error" data-error-for="gender"></span>
          </label>
        </div>

        <label class="field">
          <span class="field__label">محافظة الميلاد</span>
          <select class="field__select" name="birth_governorate_id" id="gov-select">
            <option value="">اختر…</option>
          </select>
        </label>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:.6rem">
          <label class="field">
            <span class="field__label">فصيلة الدم</span>
            <select class="field__select" name="blood_type">
              <option value="">غير محددة</option>
              ${['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
                .map((t) => `<option value="${t}">${t}</option>`).join('')}
            </select>
          </label>
          <label class="field">
            <span class="field__label">المهنة</span>
            <input class="field__input" type="text" name="occupation">
          </label>
        </div>

        <button type="submit" class="btn btn--primary btn--block">تسجيل</button>
      </form>`;

    loadGovernorates(container);

    const form = container.querySelector('#person-form');
    form.addEventListener('submit', (event) => submitForm(event, form, container));
  }

  async function loadGovernorates(container) {
    const select = container.querySelector('#gov-select');
    if (!select) return;

    try {
      const governorates = await API.governorates();
      select.insertAdjacentHTML(
        'beforeend',
        governorates
          .map((g) => `<option value="${g.id}">${UI.escape(g.name_ar)}</option>`)
          .join('')
      );
    } catch {
      // القائمة اختيارية — يبقى الحقل فارغاً دون تعطيل النموذج
    }
  }

  async function submitForm(event, form, container) {
    event.preventDefault();

    const button = form.querySelector('button[type="submit"]');
    const errorBox = form.querySelector('#form-error');
    errorBox.hidden = true;

    const values = UI.formValues(form);
    if (values.birth_governorate_id) {
      values.birth_governorate_id = Number(values.birth_governorate_id);
    }

    UI.setLoading(button, true, 'تسجيل');

    try {
      const person = await API.createPerson(values);
      UI.toast('تم تسجيل الشخص بنجاح', 'success');
      location.hash = `#/person/${person.id}`;
    } catch (error) {
      if (error.fields && error.fields.length) {
        UI.showFieldErrors(form, error.fields);
        errorBox.textContent = 'راجع الحقول المُعلَّمة';
      } else {
        errorBox.textContent = error.message;
      }
      errorBox.hidden = false;
      UI.setLoading(button, false, 'تسجيل');
    }
  }

  return { renderDetail, renderTree, renderForm };
})();
