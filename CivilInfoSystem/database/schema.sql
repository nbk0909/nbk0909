-- =============================================================================
--  نظام المعلومات المدنية الشامل — مخطط قاعدة البيانات
--  Civil Information System — Database Schema
--  المحرّك المستهدف: PostgreSQL 15+
-- =============================================================================
--  ملاحظات عامة:
--    * الحذف في هذا النظام حذف منطقي (Soft Delete) عبر العمود deleted_at.
--      لا تُحذف أي سجلات مدنية حذفاً فعلياً إطلاقاً.
--    * كل جدول يحمل أعمدة تدقيق: created_at, updated_at, created_by, updated_by.
--    * الحقول النصية العربية تُخزَّن مرتين: القيمة الأصلية + قيمة مُطبَّعة
--      (بلاحقة _normalized) تُستخدم في البحث لتجاهل التشكيل وصور الألف والياء.
-- =============================================================================

BEGIN;

-- الامتدادات المطلوبة
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- توليد المعرّفات الفريدة
CREATE EXTENSION IF NOT EXISTS "pg_trgm";     -- البحث التقريبي (Fuzzy) في الأسماء
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- =============================================================================
--  0) الأنواع المعدودة (ENUM Types)
-- =============================================================================

CREATE TYPE gender_enum            AS ENUM ('ذكر', 'أنثى');
CREATE TYPE life_status_enum       AS ENUM ('حي', 'متوفى', 'مفقود');
CREATE TYPE marital_status_enum    AS ENUM ('أعزب', 'متزوج', 'مطلق', 'أرمل');
CREATE TYPE blood_type_enum        AS ENUM ('A+','A-','B+','B-','AB+','AB-','O+','O-');
CREATE TYPE relation_type_enum     AS ENUM ('أب', 'أم', 'ابن', 'ابنة', 'زوج', 'زوجة', 'أخ', 'أخت');
CREATE TYPE document_type_enum     AS ENUM ('بطاقة وطنية', 'جواز سفر', 'شهادة جنسية', 'بطاقة عائلية');
CREATE TYPE document_status_enum   AS ENUM ('سارية', 'منتهية', 'مفقودة', 'بدل فاقد', 'ملغاة');
CREATE TYPE request_type_enum      AS ENUM ('إصدار', 'تعديل', 'بدل ضائع', 'تجديد', 'إلغاء');
CREATE TYPE request_status_enum    AS ENUM ('مقدَّم', 'قيد المراجعة', 'مقبول', 'مرفوض', 'ملغى');
CREATE TYPE audit_action_enum      AS ENUM ('إنشاء', 'قراءة', 'تعديل', 'حذف', 'اعتماد', 'دخول', 'خروج', 'محاولة فاشلة');

-- =============================================================================
--  1) تطبيع النص العربي — دالة تُستخدم في الفهارس والبحث
-- =============================================================================
--  توحّد صور الألف (أ إ آ ٱ → ا)، والتاء المربوطة (ة → ه)، والألف المقصورة (ى → ي)،
--  والهمزات (ؤ → و ، ئ → ي)، وتحذف التشكيل والتطويل، وتضغط المسافات.

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

-- =============================================================================
--  2) التقسيمات الإدارية
-- =============================================================================

CREATE TABLE governorates (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(10)  NOT NULL UNIQUE,
    name_ar         VARCHAR(100) NOT NULL UNIQUE,
    name_en         VARCHAR(100),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
COMMENT ON TABLE governorates IS 'المحافظات';

CREATE TABLE districts (
    id              SERIAL PRIMARY KEY,
    governorate_id  INTEGER      NOT NULL REFERENCES governorates(id) ON DELETE RESTRICT,
    code            VARCHAR(10)  NOT NULL,
    name_ar         VARCHAR(100) NOT NULL,
    name_en         VARCHAR(100),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    CONSTRAINT uq_district_code UNIQUE (governorate_id, code)
);
COMMENT ON TABLE districts IS 'الأقضية / المناطق';

CREATE TABLE subdistricts (
    id              SERIAL PRIMARY KEY,
    district_id     INTEGER      NOT NULL REFERENCES districts(id) ON DELETE RESTRICT,
    code            VARCHAR(10)  NOT NULL,
    name_ar         VARCHAR(100) NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    CONSTRAINT uq_subdistrict_code UNIQUE (district_id, code)
);
COMMENT ON TABLE subdistricts IS 'النواحي';

CREATE INDEX idx_districts_gov      ON districts(governorate_id)  WHERE deleted_at IS NULL;
CREATE INDEX idx_subdistricts_dist  ON subdistricts(district_id)  WHERE deleted_at IS NULL;

-- =============================================================================
--  3) المستخدمون والصلاحيات (RBAC)
-- =============================================================================

CREATE TABLE roles (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(50)  NOT NULL UNIQUE,   -- admin, registrar, clerk, auditor, viewer
    name_ar         VARCHAR(100) NOT NULL,
    description_ar  TEXT,
    is_system       BOOLEAN      NOT NULL DEFAULT FALSE,  -- أدوار النظام لا تُحذف
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
COMMENT ON TABLE roles IS 'الأدوار الوظيفية';

CREATE TABLE permissions (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(100) NOT NULL UNIQUE,   -- مثال: persons.create
    resource        VARCHAR(50)  NOT NULL,          -- persons
    action          VARCHAR(30)  NOT NULL,          -- create/read/update/delete/approve
    name_ar         VARCHAR(150) NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE permissions IS 'الصلاحيات الدقيقة';

CREATE TABLE role_permissions (
    role_id         INTEGER NOT NULL REFERENCES roles(id)       ON DELETE CASCADE,
    permission_id   INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE users (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username                VARCHAR(50)  NOT NULL UNIQUE,
    email                   VARCHAR(150) UNIQUE,
    password_hash           VARCHAR(255) NOT NULL,
    full_name_ar            VARCHAR(200) NOT NULL,
    phone                   VARCHAR(20),
    governorate_id          INTEGER REFERENCES governorates(id),  -- نطاق عمل الموظف

    is_active               BOOLEAN     NOT NULL DEFAULT TRUE,
    must_change_password    BOOLEAN     NOT NULL DEFAULT TRUE,

    -- المصادقة الثنائية
    totp_secret_encrypted   TEXT,
    totp_enabled            BOOLEAN     NOT NULL DEFAULT FALSE,

    -- حماية من محاولات الدخول المتكررة
    failed_login_attempts   SMALLINT    NOT NULL DEFAULT 0,
    locked_until            TIMESTAMPTZ,
    last_login_at           TIMESTAMPTZ,
    password_changed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at              TIMESTAMPTZ,
    created_by              UUID REFERENCES users(id),
    updated_by              UUID REFERENCES users(id),

    CONSTRAINT ck_failed_attempts CHECK (failed_login_attempts >= 0)
);
COMMENT ON TABLE users IS 'مستخدمو النظام';

CREATE TABLE user_roles (
    user_id     UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id     INTEGER NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_by UUID REFERENCES users(id),
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE refresh_tokens (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      VARCHAR(255) NOT NULL UNIQUE,
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,
    user_agent      VARCHAR(300),
    ip_address      INET,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE refresh_tokens IS 'رموز التحديث للجلسات';

CREATE INDEX idx_users_active        ON users(username) WHERE deleted_at IS NULL AND is_active;
CREATE INDEX idx_refresh_user        ON refresh_tokens(user_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_refresh_expires     ON refresh_tokens(expires_at);

-- =============================================================================
--  4) الأشخاص — السجل المدني الأساسي
-- =============================================================================

CREATE TABLE persons (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- الرقم الوطني: 12 رقماً، يُتحقق من صحته في طبقة التطبيق بخوارزمية Luhn المعدّلة
    national_id             VARCHAR(12)  NOT NULL UNIQUE,

    -- الاسم الرباعي
    first_name              VARCHAR(50)  NOT NULL,
    father_name             VARCHAR(50)  NOT NULL,
    grandfather_name        VARCHAR(50)  NOT NULL,
    family_name             VARCHAR(50)  NOT NULL,
    mother_full_name        VARCHAR(150) NOT NULL,

    -- الاسم المُطبَّع للبحث (يُملأ تلقائياً بمُشغّل Trigger)
    full_name_normalized    VARCHAR(300),

    -- الميلاد
    birth_date              DATE         NOT NULL,
    birth_date_hijri        VARCHAR(12),                       -- بصيغة YYYY-MM-DD هجري
    birth_governorate_id    INTEGER REFERENCES governorates(id),
    birth_place_detail      VARCHAR(200),

    gender                  gender_enum        NOT NULL,
    nationality             VARCHAR(60)        NOT NULL DEFAULT 'عراقي',
    religion                VARCHAR(50),
    blood_type              blood_type_enum,
    marital_status          marital_status_enum NOT NULL DEFAULT 'أعزب',
    occupation              VARCHAR(100),
    education_level         VARCHAR(100),

    life_status             life_status_enum   NOT NULL DEFAULT 'حي',

    -- المرفقات البيومترية (مسارات تخزين، لا تُخزَّن الملفات في قاعدة البيانات)
    photo_path              VARCHAR(300),
    fingerprint_path        VARCHAR(300),

    notes                   TEXT,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at              TIMESTAMPTZ,
    created_by              UUID REFERENCES users(id),
    updated_by              UUID REFERENCES users(id),

    CONSTRAINT ck_national_id_format CHECK (national_id ~ '^[0-9]{12}$'),
    CONSTRAINT ck_birth_not_future   CHECK (birth_date <= CURRENT_DATE)
);
COMMENT ON TABLE persons IS 'السجل المدني الأساسي للأشخاص';

-- مُشغّل يملأ الاسم المطبَّع تلقائياً عند الإدراج أو التعديل
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

-- الفهارس المطلوبة للبحث السريع
CREATE INDEX idx_persons_national_id   ON persons(national_id)           WHERE deleted_at IS NULL;
CREATE INDEX idx_persons_name_norm     ON persons(full_name_normalized)  WHERE deleted_at IS NULL;
CREATE INDEX idx_persons_name_trgm     ON persons USING GIN (full_name_normalized gin_trgm_ops);
CREATE INDEX idx_persons_birth_date    ON persons(birth_date)            WHERE deleted_at IS NULL;
CREATE INDEX idx_persons_life_status   ON persons(life_status)           WHERE deleted_at IS NULL;
CREATE INDEX idx_persons_birth_gov     ON persons(birth_governorate_id)  WHERE deleted_at IS NULL;

-- =============================================================================
--  5) العناوين والسكن (مع سجل تاريخي للتنقّلات)
-- =============================================================================

CREATE TABLE addresses (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id       UUID    NOT NULL REFERENCES persons(id) ON DELETE RESTRICT,
    governorate_id  INTEGER NOT NULL REFERENCES governorates(id),
    district_id     INTEGER REFERENCES districts(id),
    subdistrict_id  INTEGER REFERENCES subdistricts(id),
    quarter         VARCHAR(100),        -- المحلة
    street          VARCHAR(100),        -- الزقاق
    house_number    VARCHAR(20),         -- رقم الدار
    postal_code     VARCHAR(10),
    details         TEXT,

    valid_from      DATE    NOT NULL DEFAULT CURRENT_DATE,
    valid_to        DATE,                -- NULL يعني العنوان الحالي
    is_current      BOOLEAN NOT NULL DEFAULT TRUE,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    created_by      UUID REFERENCES users(id),
    updated_by      UUID REFERENCES users(id),

    CONSTRAINT ck_address_period CHECK (valid_to IS NULL OR valid_to >= valid_from)
);
COMMENT ON TABLE addresses IS 'عناوين السكن مع السجل التاريخي للتنقّلات';

-- عنوان حالي واحد فقط لكل شخص
CREATE UNIQUE INDEX uq_address_current
    ON addresses(person_id)
    WHERE is_current AND deleted_at IS NULL;

CREATE INDEX idx_addresses_person ON addresses(person_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_addresses_gov    ON addresses(governorate_id) WHERE deleted_at IS NULL;

-- =============================================================================
--  6) العلاقات الأُسرية وشجرة العائلة
-- =============================================================================

CREATE TABLE family_relations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id       UUID NOT NULL REFERENCES persons(id) ON DELETE RESTRICT,
    related_person_id UUID NOT NULL REFERENCES persons(id) ON DELETE RESTRICT,
    relation_type   relation_type_enum NOT NULL,   -- علاقة related_person بالنسبة لـ person

    start_date      DATE,
    end_date        DATE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    created_by      UUID REFERENCES users(id),

    -- منع أن يكون الشخص قريباً لنفسه
    CONSTRAINT ck_no_self_relation CHECK (person_id <> related_person_id),
    CONSTRAINT ck_relation_period  CHECK (end_date IS NULL OR end_date >= start_date),
    CONSTRAINT uq_relation UNIQUE (person_id, related_person_id, relation_type)
);
COMMENT ON TABLE family_relations IS 'العلاقات الأُسرية — تُخزَّن باتجاهين لتسهيل الاستعلام';

CREATE INDEX idx_relations_person    ON family_relations(person_id)         WHERE deleted_at IS NULL;
CREATE INDEX idx_relations_related   ON family_relations(related_person_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_relations_type      ON family_relations(relation_type)     WHERE deleted_at IS NULL;

-- =============================================================================
--  7) بطاقة العائلة (دفتر العائلة)
-- =============================================================================

CREATE TABLE family_cards (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    card_number     VARCHAR(20) NOT NULL UNIQUE,
    head_person_id  UUID        NOT NULL REFERENCES persons(id) ON DELETE RESTRICT,
    governorate_id  INTEGER     NOT NULL REFERENCES governorates(id),
    issue_date      DATE        NOT NULL DEFAULT CURRENT_DATE,
    issuing_office  VARCHAR(150),
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    created_by      UUID REFERENCES users(id),
    updated_by      UUID REFERENCES users(id)
);
COMMENT ON TABLE family_cards IS 'بطاقات العائلة (دفتر العائلة)';

CREATE TABLE family_card_members (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    family_card_id  UUID NOT NULL REFERENCES family_cards(id) ON DELETE CASCADE,
    person_id       UUID NOT NULL REFERENCES persons(id)      ON DELETE RESTRICT,
    relation_to_head relation_type_enum NOT NULL,
    added_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    removed_at      TIMESTAMPTZ,
    CONSTRAINT uq_card_member UNIQUE (family_card_id, person_id)
);

-- الشخص لا ينتمي لأكثر من بطاقة عائلة نشطة
CREATE UNIQUE INDEX uq_person_active_card
    ON family_card_members(person_id)
    WHERE removed_at IS NULL;

CREATE INDEX idx_card_members_card ON family_card_members(family_card_id);

-- =============================================================================
--  8) واقعات الميلاد
-- =============================================================================

CREATE TABLE birth_records (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    record_number       VARCHAR(20) NOT NULL UNIQUE,
    person_id           UUID        NOT NULL UNIQUE REFERENCES persons(id) ON DELETE RESTRICT,
    father_id           UUID REFERENCES persons(id),
    mother_id           UUID REFERENCES persons(id),

    birth_date          DATE        NOT NULL,
    birth_time          TIME,
    hospital_name       VARCHAR(200),
    governorate_id      INTEGER     NOT NULL REFERENCES governorates(id),
    birth_weight_grams  INTEGER,
    delivery_type       VARCHAR(50),          -- طبيعية / قيصرية
    attending_physician VARCHAR(150),
    informant_name      VARCHAR(200),         -- اسم المبلِّغ
    informant_relation  VARCHAR(50),

    registration_date   DATE        NOT NULL DEFAULT CURRENT_DATE,
    registration_office VARCHAR(150),
    certificate_issued  BOOLEAN     NOT NULL DEFAULT FALSE,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ,
    created_by          UUID REFERENCES users(id),
    updated_by          UUID REFERENCES users(id),

    CONSTRAINT ck_birth_weight  CHECK (birth_weight_grams IS NULL OR birth_weight_grams BETWEEN 200 AND 8000),
    CONSTRAINT ck_birth_reg     CHECK (registration_date >= birth_date),
    CONSTRAINT ck_parents_differ CHECK (father_id IS NULL OR mother_id IS NULL OR father_id <> mother_id)
);
COMMENT ON TABLE birth_records IS 'واقعات الميلاد';

CREATE INDEX idx_births_date   ON birth_records(birth_date)     WHERE deleted_at IS NULL;
CREATE INDEX idx_births_father ON birth_records(father_id)      WHERE deleted_at IS NULL;
CREATE INDEX idx_births_mother ON birth_records(mother_id)      WHERE deleted_at IS NULL;
CREATE INDEX idx_births_gov    ON birth_records(governorate_id) WHERE deleted_at IS NULL;

-- =============================================================================
--  9) واقعات الوفاة
-- =============================================================================

CREATE TABLE death_records (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    record_number       VARCHAR(20) NOT NULL UNIQUE,
    person_id           UUID        NOT NULL UNIQUE REFERENCES persons(id) ON DELETE RESTRICT,

    death_date          DATE        NOT NULL,
    death_time          TIME,
    death_place         VARCHAR(200),
    governorate_id      INTEGER     NOT NULL REFERENCES governorates(id),
    cause_of_death      VARCHAR(300),
    cause_category      VARCHAR(100),         -- طبيعية / حادث / أخرى
    reporting_authority VARCHAR(200),         -- الجهة المبلِّغة
    certifying_physician VARCHAR(150),
    burial_place        VARCHAR(200),

    registration_date   DATE        NOT NULL DEFAULT CURRENT_DATE,
    certificate_issued  BOOLEAN     NOT NULL DEFAULT FALSE,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ,
    created_by          UUID REFERENCES users(id),
    updated_by          UUID REFERENCES users(id),

    CONSTRAINT ck_death_not_future CHECK (death_date <= CURRENT_DATE),
    CONSTRAINT ck_death_reg        CHECK (registration_date >= death_date)
);
COMMENT ON TABLE death_records IS 'واقعات الوفاة';

-- قيد منطقي: تاريخ الوفاة لا يسبق تاريخ الميلاد (يُفحص بمُشغّل لأنه عبر جدولين)
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

-- تحديث حالة الشخص تلقائياً عند تسجيل الوفاة
CREATE OR REPLACE FUNCTION apply_death_to_person()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE persons
       SET life_status = 'متوفى',
           updated_at  = NOW()
     WHERE id = NEW.person_id;

    -- إنهاء علاقات الزوجية النشطة
    UPDATE family_relations
       SET is_active = FALSE,
           end_date  = NEW.death_date,
           updated_at = NOW()
     WHERE is_active
       AND relation_type IN ('زوج', 'زوجة')
       AND (person_id = NEW.person_id OR related_person_id = NEW.person_id);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_apply_death
    AFTER INSERT ON death_records
    FOR EACH ROW EXECUTE FUNCTION apply_death_to_person();

CREATE INDEX idx_deaths_date ON death_records(death_date)     WHERE deleted_at IS NULL;
CREATE INDEX idx_deaths_gov  ON death_records(governorate_id) WHERE deleted_at IS NULL;

-- =============================================================================
--  10) عقود الزواج والطلاق
-- =============================================================================

CREATE TABLE marriage_contracts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_number     VARCHAR(20) NOT NULL UNIQUE,
    husband_id          UUID        NOT NULL REFERENCES persons(id) ON DELETE RESTRICT,
    wife_id             UUID        NOT NULL REFERENCES persons(id) ON DELETE RESTRICT,

    contract_date       DATE        NOT NULL,
    contract_date_hijri VARCHAR(12),
    governorate_id      INTEGER     NOT NULL REFERENCES governorates(id),
    court_name          VARCHAR(200),
    officiant_name      VARCHAR(150) NOT NULL,   -- المأذون / القاضي
    witness1_name       VARCHAR(150) NOT NULL,
    witness1_national_id VARCHAR(12),
    witness2_name       VARCHAR(150) NOT NULL,
    witness2_national_id VARCHAR(12),

    dowry_prompt        NUMERIC(14,2),           -- المهر المعجّل
    dowry_deferred      NUMERIC(14,2),           -- المهر المؤجّل
    currency            VARCHAR(10) NOT NULL DEFAULT 'IQD',

    is_active           BOOLEAN     NOT NULL DEFAULT TRUE,
    document_issued     BOOLEAN     NOT NULL DEFAULT FALSE,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ,
    created_by          UUID REFERENCES users(id),
    updated_by          UUID REFERENCES users(id),

    CONSTRAINT ck_spouses_differ CHECK (husband_id <> wife_id),
    CONSTRAINT ck_dowry_positive CHECK (
        (dowry_prompt   IS NULL OR dowry_prompt   >= 0) AND
        (dowry_deferred IS NULL OR dowry_deferred >= 0)
    ),
    CONSTRAINT ck_contract_not_future CHECK (contract_date <= CURRENT_DATE)
);
COMMENT ON TABLE marriage_contracts IS 'عقود الزواج';

CREATE INDEX idx_marriage_husband ON marriage_contracts(husband_id)   WHERE deleted_at IS NULL;
CREATE INDEX idx_marriage_wife    ON marriage_contracts(wife_id)      WHERE deleted_at IS NULL;
CREATE INDEX idx_marriage_date    ON marriage_contracts(contract_date) WHERE deleted_at IS NULL;

CREATE TABLE divorce_records (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    record_number       VARCHAR(20) NOT NULL UNIQUE,
    marriage_id         UUID        NOT NULL REFERENCES marriage_contracts(id) ON DELETE RESTRICT,

    divorce_date        DATE        NOT NULL,
    divorce_date_hijri  VARCHAR(12),
    divorce_type        VARCHAR(50),        -- رجعي / بائن / خُلع
    court_name          VARCHAR(200),
    judge_name          VARCHAR(150),
    reason              TEXT,
    custody_notes       TEXT,               -- ترتيبات الحضانة
    document_issued     BOOLEAN     NOT NULL DEFAULT FALSE,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ,
    created_by          UUID REFERENCES users(id),
    updated_by          UUID REFERENCES users(id),

    CONSTRAINT ck_divorce_not_future CHECK (divorce_date <= CURRENT_DATE)
);
COMMENT ON TABLE divorce_records IS 'واقعات الطلاق';

-- الطلاق لا يسبق عقد الزواج
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

CREATE INDEX idx_divorce_marriage ON divorce_records(marriage_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_divorce_date     ON divorce_records(divorce_date) WHERE deleted_at IS NULL;

-- =============================================================================
--  11) الوثائق والهويات
-- =============================================================================

CREATE TABLE documents (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id           UUID                NOT NULL REFERENCES persons(id) ON DELETE RESTRICT,
    document_type       document_type_enum  NOT NULL,
    document_number     VARCHAR(30)         NOT NULL,

    issue_date          DATE                NOT NULL,
    expiry_date         DATE,
    issuing_authority   VARCHAR(200)        NOT NULL,
    issuing_governorate_id INTEGER REFERENCES governorates(id),
    status              document_status_enum NOT NULL DEFAULT 'سارية',

    replaces_document_id UUID REFERENCES documents(id),   -- في حالة بدل الفاقد
    scan_path           VARCHAR(300),
    notes               TEXT,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ,
    created_by          UUID REFERENCES users(id),
    updated_by          UUID REFERENCES users(id),

    CONSTRAINT uq_document       UNIQUE (document_type, document_number),
    CONSTRAINT ck_document_dates CHECK (expiry_date IS NULL OR expiry_date > issue_date)
);
COMMENT ON TABLE documents IS 'الوثائق والهويات الرسمية';

-- وثيقة سارية واحدة فقط من كل نوع لكل شخص
CREATE UNIQUE INDEX uq_active_document_per_type
    ON documents(person_id, document_type)
    WHERE status = 'سارية' AND deleted_at IS NULL;

CREATE INDEX idx_documents_person ON documents(person_id)       WHERE deleted_at IS NULL;
CREATE INDEX idx_documents_number ON documents(document_number) WHERE deleted_at IS NULL;
CREATE INDEX idx_documents_expiry ON documents(expiry_date)     WHERE deleted_at IS NULL;

-- =============================================================================
--  12) المعاملات والطلبات
-- =============================================================================

CREATE TABLE service_requests (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference_number    VARCHAR(25)         NOT NULL UNIQUE,   -- رقم مرجعي للمواطن
    person_id           UUID                NOT NULL REFERENCES persons(id) ON DELETE RESTRICT,
    request_type        request_type_enum   NOT NULL,
    subject             VARCHAR(200)        NOT NULL,
    details             TEXT,
    status              request_status_enum NOT NULL DEFAULT 'مقدَّم',

    submitted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    submitted_by        UUID REFERENCES users(id),
    reviewed_at         TIMESTAMPTZ,
    reviewed_by         UUID REFERENCES users(id),
    decision_at         TIMESTAMPTZ,
    decision_by         UUID REFERENCES users(id),
    rejection_reason    TEXT,

    fee_amount          NUMERIC(12,2) NOT NULL DEFAULT 0,
    fee_paid            BOOLEAN       NOT NULL DEFAULT FALSE,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ,

    CONSTRAINT ck_fee_positive CHECK (fee_amount >= 0),
    -- الرفض يستوجب ذكر السبب
    CONSTRAINT ck_rejection_reason CHECK (status <> 'مرفوض' OR rejection_reason IS NOT NULL)
);
COMMENT ON TABLE service_requests IS 'المعاملات وطلبات الخدمة';

CREATE TABLE request_attachments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id      UUID         NOT NULL REFERENCES service_requests(id) ON DELETE CASCADE,
    file_name       VARCHAR(255) NOT NULL,
    file_path       VARCHAR(300) NOT NULL,
    mime_type       VARCHAR(100),
    file_size_bytes BIGINT,
    uploaded_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    uploaded_by     UUID REFERENCES users(id)
);

CREATE INDEX idx_requests_person ON service_requests(person_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_requests_status ON service_requests(status)    WHERE deleted_at IS NULL;
CREATE INDEX idx_requests_ref    ON service_requests(reference_number);

-- =============================================================================
--  13) سجل التدقيق (Audit Log)
-- =============================================================================

CREATE TABLE audit_log (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id),
    username        VARCHAR(50),            -- نسخة ثابتة تبقى حتى لو عُطّل الحساب
    action          audit_action_enum NOT NULL,
    resource_type   VARCHAR(50)       NOT NULL,
    resource_id     VARCHAR(50),
    old_values      JSONB,                  -- القيم قبل التعديل
    new_values      JSONB,                  -- القيم بعد التعديل
    ip_address      INET,
    user_agent      VARCHAR(300),
    request_path    VARCHAR(300),
    succeeded       BOOLEAN NOT NULL DEFAULT TRUE,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE audit_log IS 'سجل التدقيق — لا يُعدَّل ولا يُحذف منه شيء';

CREATE INDEX idx_audit_user     ON audit_log(user_id);
CREATE INDEX idx_audit_resource ON audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_created  ON audit_log(created_at DESC);
CREATE INDEX idx_audit_action   ON audit_log(action);

-- =============================================================================
--  14) عروض مساعدة (Views)
-- =============================================================================

-- عرض مبسّط للأشخاص الأحياء مع عناوينهم الحالية
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

COMMIT;

-- =============================================================================
--  نهاية المخطط
-- =============================================================================
