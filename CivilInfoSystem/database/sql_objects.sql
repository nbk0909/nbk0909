-- =============================================================================
--  الدوال والمُشغّلات والعروض
-- =============================================================================
--  هذا الملف يُكتب يدوياً — يحتوي ما لا تستطيع نماذج ORM التعبير عنه.
--  يُلحق آلياً بنهاية database/schema.sql عند التوليد، فلا تُنفّذه منفرداً.
-- =============================================================================

-- ---------------------------------------------------------------------------
--  1) تطبيع النص العربي
-- ---------------------------------------------------------------------------
--  توحّد صور الألف (أ إ آ ٱ → ا)، والتاء المربوطة (ة → ه)، والألف المقصورة
--  (ى → ي)، والهمزات (ؤ → و ، ئ → ي)، وتحذف التشكيل والتطويل، وتضغط المسافات.
--  النسخة نفسها مُنفَّذة في بايثون في app/utils/arabic.py — أي تعديل هنا يجب
--  أن يقابله تعديل هناك، وإلا اختلفت نتائج البحث بين الطبقتين.

CREATE OR REPLACE FUNCTION normalize_arabic(txt TEXT)
RETURNS TEXT AS $$
BEGIN
    IF txt IS NULL THEN
        RETURN NULL;
    END IF;

    RETURN btrim(
        regexp_replace(
            translate(
                -- حذف التشكيل (الفتحة..السكون + الشدة) والتطويل
                regexp_replace(txt, '[ً-ْـٰ]', '', 'g'),
                'أإآٱؤئةى',
                'ااااويهي'
            ),
            '\s+', ' ', 'g'
        )
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE STRICT;

COMMENT ON FUNCTION normalize_arabic(TEXT) IS
    'تطبيع النص العربي للبحث: توحيد الألف والياء والتاء المربوطة وحذف التشكيل';


-- ---------------------------------------------------------------------------
--  2) ملء الاسم المطبَّع تلقائياً عند الإدراج والتعديل
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION persons_fill_normalized()
RETURNS TRIGGER AS $$
BEGIN
    NEW.full_name_normalized := normalize_arabic(
        NEW.first_name || ' ' || NEW.father_name || ' ' ||
        NEW.grandfather_name || ' ' || NEW.family_name
    );
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_persons_normalize
    BEFORE INSERT OR UPDATE ON persons
    FOR EACH ROW EXECUTE FUNCTION persons_fill_normalized();


-- ---------------------------------------------------------------------------
--  3) قيود منطقية عبر أكثر من جدول
-- ---------------------------------------------------------------------------
--  قيود CHECK لا تستطيع قراءة جداول أخرى، فتُفرض هذه القواعد بمُشغّلات.

-- تاريخ الوفاة لا يسبق تاريخ الميلاد
CREATE OR REPLACE FUNCTION check_death_after_birth()
RETURNS TRIGGER AS $$
DECLARE
    v_birth_date DATE;
BEGIN
    SELECT birth_date INTO v_birth_date FROM persons WHERE id = NEW.person_id;

    IF v_birth_date IS NOT NULL AND NEW.death_date < v_birth_date THEN
        RAISE EXCEPTION 'تاريخ الوفاة (%) لا يمكن أن يسبق تاريخ الميلاد (%)',
            NEW.death_date, v_birth_date;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_death_after_birth
    BEFORE INSERT OR UPDATE ON death_records
    FOR EACH ROW EXECUTE FUNCTION check_death_after_birth();


-- تاريخ الطلاق لا يسبق تاريخ عقد الزواج
CREATE OR REPLACE FUNCTION check_divorce_after_marriage()
RETURNS TRIGGER AS $$
DECLARE
    v_contract_date DATE;
BEGIN
    SELECT contract_date INTO v_contract_date
      FROM marriage_contracts WHERE id = NEW.marriage_id;

    IF v_contract_date IS NOT NULL AND NEW.divorce_date < v_contract_date THEN
        RAISE EXCEPTION 'تاريخ الطلاق (%) لا يمكن أن يسبق تاريخ عقد الزواج (%)',
            NEW.divorce_date, v_contract_date;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_divorce_after_marriage
    BEFORE INSERT OR UPDATE ON divorce_records
    FOR EACH ROW EXECUTE FUNCTION check_divorce_after_marriage();


-- المولود لا يسبق أباه أو أمه في الميلاد
CREATE OR REPLACE FUNCTION check_child_after_parents()
RETURNS TRIGGER AS $$
DECLARE
    v_parent_birth DATE;
BEGIN
    FOR v_parent_birth IN
        SELECT birth_date FROM persons
         WHERE id IN (NEW.father_id, NEW.mother_id)
    LOOP
        IF NEW.birth_date <= v_parent_birth THEN
            RAISE EXCEPTION 'تاريخ ميلاد المولود (%) يجب أن يكون بعد تاريخ ميلاد والديه (%)',
                NEW.birth_date, v_parent_birth;
        END IF;
    END LOOP;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_child_after_parents
    BEFORE INSERT OR UPDATE ON birth_records
    FOR EACH ROW EXECUTE FUNCTION check_child_after_parents();


-- ---------------------------------------------------------------------------
--  4) أثر تسجيل الوفاة على السجلات المرتبطة
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION apply_death_to_person()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE persons
       SET life_status = 'متوفى',
           updated_at  = NOW()
     WHERE id = NEW.person_id;

    -- إنهاء علاقات الزوجية النشطة
    UPDATE family_relations
       SET is_active  = FALSE,
           end_date   = NEW.death_date,
           updated_at = NOW()
     WHERE is_active
       AND relation_type IN ('زوج', 'زوجة')
       AND (person_id = NEW.person_id OR related_person_id = NEW.person_id);

    -- ترمُّل الزوج الباقي على قيد الحياة
    UPDATE persons
       SET marital_status = 'أرمل',
           updated_at     = NOW()
     WHERE life_status = 'حي'
       AND id IN (
           SELECT CASE WHEN husband_id = NEW.person_id THEN wife_id ELSE husband_id END
             FROM marriage_contracts
            WHERE is_active
              AND deleted_at IS NULL
              AND (husband_id = NEW.person_id OR wife_id = NEW.person_id)
       );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_apply_death
    AFTER INSERT ON death_records
    FOR EACH ROW EXECUTE FUNCTION apply_death_to_person();


-- ---------------------------------------------------------------------------
--  5) عروض مساعدة
-- ---------------------------------------------------------------------------

-- الأشخاص مع عناوينهم الحالية وأعمارهم
CREATE OR REPLACE VIEW v_persons_current AS
SELECT
    p.id,
    p.national_id,
    p.first_name || ' ' || p.father_name || ' ' ||
        p.grandfather_name || ' ' || p.family_name AS full_name,
    p.birth_date,
    date_part('year', age(p.birth_date))::INTEGER   AS age_years,
    p.gender,
    p.marital_status,
    p.life_status,
    g.name_ar                                        AS governorate,
    a.quarter,
    a.street,
    a.house_number
FROM persons p
LEFT JOIN addresses    a ON a.person_id = p.id AND a.is_current AND a.deleted_at IS NULL
LEFT JOIN governorates g ON g.id = a.governorate_id
WHERE p.deleted_at IS NULL;

COMMENT ON VIEW v_persons_current IS 'الأشخاص مع عناوينهم الحالية وأعمارهم';


-- إحصاء سكاني حسب المحافظة والجنس
CREATE OR REPLACE VIEW v_population_stats AS
SELECT
    g.name_ar                                    AS governorate,
    p.gender,
    COUNT(*) FILTER (WHERE p.life_status = 'حي') AS alive_count,
    COUNT(*)                                     AS total_count
FROM persons p
JOIN addresses    a ON a.person_id = p.id AND a.is_current AND a.deleted_at IS NULL
JOIN governorates g ON g.id = a.governorate_id
WHERE p.deleted_at IS NULL
GROUP BY g.name_ar, p.gender;

COMMENT ON VIEW v_population_stats IS 'إحصاء السكان حسب المحافظة والجنس';


-- الوثائق التي أوشكت على الانتهاء (خلال 90 يوماً)
CREATE OR REPLACE VIEW v_expiring_documents AS
SELECT
    d.id,
    d.document_type,
    d.document_number,
    d.expiry_date,
    (d.expiry_date - CURRENT_DATE) AS days_remaining,
    p.national_id,
    p.first_name || ' ' || p.father_name || ' ' ||
        p.grandfather_name || ' ' || p.family_name AS full_name
FROM documents d
JOIN persons p ON p.id = d.person_id
WHERE d.deleted_at IS NULL
  AND p.deleted_at IS NULL
  AND d.status = 'سارية'
  AND d.expiry_date IS NOT NULL
  AND d.expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '90 days';

COMMENT ON VIEW v_expiring_documents IS 'الوثائق السارية التي تنتهي خلال 90 يوماً';
