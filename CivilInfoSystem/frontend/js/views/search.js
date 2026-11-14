/* =============================================================================
   شاشة البحث في السجل المدني
   ============================================================================= */

const SearchView = (() => {
  'use strict';

  let debounceTimer = null;
  let activeRequest = 0;   // يتجاهل استجابات الطلبات التي سبقتها أحدث منها

  function render(container) {
    container.innerHTML = `
      <form id="search-form" class="card" role="search">
        <label class="field" style="margin-bottom:.6rem">
          <span class="field__label">بحث سريع</span>
          <input class="field__input" type="search" name="q" id="search-q"
                 placeholder="الاسم أو الرقم الوطني أو رقم الوثيقة"
                 autocomplete="off" enterkeyhint="search">
          <span class="field__hint">
            البحث يتجاهل التشكيل وصور الهمزة، ويجد الاسم رغم الخطأ الإملائي
          </span>
        </label>

        <details id="advanced">
          <summary style="cursor:pointer;min-height:var(--touch);display:flex;align-items:center;font-size:.9rem;font-weight:600">
            بحث متقدّم
          </summary>

          <div style="padding-top:.75rem">
            <label class="field">
              <span class="field__label">اللقب</span>
              <input class="field__input" type="text" name="family_name" autocomplete="off">
            </label>

            <label class="field">
              <span class="field__label">اسم الأم</span>
              <input class="field__input" type="text" name="mother_name" autocomplete="off">
            </label>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:.6rem">
              <label class="field">
                <span class="field__label">من تاريخ ميلاد</span>
                <input class="field__input" type="date" name="birth_date_from">
              </label>
              <label class="field">
                <span class="field__label">إلى تاريخ</span>
                <input class="field__input" type="date" name="birth_date_to">
              </label>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:.6rem">
              <label class="field">
                <span class="field__label">الجنس</span>
                <select class="field__select" name="gender">
                  <option value="">الكل</option>
                  <option value="ذكر">ذكر</option>
                  <option value="أنثى">أنثى</option>
                </select>
              </label>
              <label class="field">
                <span class="field__label">حالة الحياة</span>
                <select class="field__select" name="life_status">
                  <option value="">الكل</option>
                  <option value="حي">حي</option>
                  <option value="متوفى">متوفى</option>
                  <option value="مفقود">مفقود</option>
                </select>
              </label>
            </div>

            <button type="submit" class="btn btn--primary btn--block">بحث</button>
          </div>
        </details>
      </form>

      <div id="search-results" aria-live="polite"></div>`;

    const form = container.querySelector('#search-form');
    const quick = container.querySelector('#search-q');

    // بحث أثناء الكتابة مع تأخير: كل ضغطة مفتاح طلب على الخادم لولاه
    quick.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      const value = quick.value.trim();

      if (value.length < 2) {
        container.querySelector('#search-results').innerHTML = '';
        return;
      }

      debounceTimer = setTimeout(() => runSearch(container, { q: value }), 350);
    });

    form.addEventListener('submit', (event) => {
      event.preventDefault();
      clearTimeout(debounceTimer);
      runSearch(container, UI.formValues(form));
    });

    setTimeout(() => quick.focus(), 60);
  }

  async function runSearch(container, params, page = 1) {
    const host = container.querySelector('#search-results');
    if (!host) return;

    const hasCriteria = Object.values(params).some((v) => v);
    if (!hasCriteria) {
      host.innerHTML = UI.errorBox('حدّد معياراً واحداً على الأقل للبحث');
      return;
    }

    const requestId = ++activeRequest;
    host.innerHTML = UI.skeletons(3);

    try {
      const result = await API.searchPersons({ ...params, page, page_size: 20 });

      // استجابة قديمة وصلت بعد أحدث منها — تُتجاهل
      if (requestId !== activeRequest) return;

      if (!result.items.length) {
        host.innerHTML = UI.empty('لا توجد نتائج مطابقة');
        return;
      }

      const fuzzy = result.items.some((item) => item.similarity !== null);

      host.innerHTML = `
        <p style="font-size:.85rem;color:var(--text-muted);margin:.25rem 0 .6rem">
          ${UI.digits(result.total)} نتيجة
          ${fuzzy ? '<span class="badge badge--warning">نتائج تقريبية</span>' : ''}
        </p>
        <div class="list">
          ${result.items.map((p) => UI.personListItem(p, { similarity: p.similarity })).join('')}
        </div>
        ${result.has_next ? `
          <button class="btn btn--ghost btn--block" id="load-more" style="margin-top:.75rem">
            عرض المزيد
          </button>` : ''}`;

      const more = host.querySelector('#load-more');
      if (more) {
        more.addEventListener('click', async () => {
          UI.setLoading(more, true, 'عرض المزيد');
          try {
            const next = await API.searchPersons({ ...params, page: page + 1, page_size: 20 });
            const list = host.querySelector('.list');
            list.insertAdjacentHTML(
              'beforeend',
              next.items.map((p) => UI.personListItem(p, { similarity: p.similarity })).join('')
            );
            if (next.has_next) {
              UI.setLoading(more, false, 'عرض المزيد');
              page += 1;
            } else {
              more.remove();
            }
          } catch (error) {
            UI.toast(error.message, 'error');
            UI.setLoading(more, false, 'عرض المزيد');
          }
        });
      }
    } catch (error) {
      if (requestId !== activeRequest) return;
      host.innerHTML = UI.errorBox(error.message);
    }
  }

  return { render };
})();
