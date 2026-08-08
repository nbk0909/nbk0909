-- =============================================================================
--  نظام المعلومات المدنية الشامل — مخطط قاعدة البيانات
--  Civil Information System — Database Schema
--  المحرّك المستهدف: PostgreSQL 15+
-- =============================================================================
--
--  ⚠️  هذا الملف مُولَّد آلياً — لا تعدّله يدوياً.
--      لتغيير بنية الجداول: عدّل النماذج في backend/app/models/
--      لتغيير الدوال والمُشغّلات والعروض: عدّل database/sql_objects.sql
--      ثم أعد التوليد:  cd backend && python -m scripts.generate_schema
--
-- =============================================================================
--  ملاحظات:
--    * الحذف حذف منطقي (Soft Delete) عبر العمود deleted_at.
--      لا تُحذف أي سجلات مدنية حذفاً فعلياً إطلاقاً.
--    * الحقول النصية العربية تُخزَّن مرتين: القيمة الأصلية + قيمة مُطبَّعة
--      (full_name_normalized) تُستخدم في البحث لتجاهل التشكيل وصور الألف.
-- =============================================================================

BEGIN;

-- الامتدادات المطلوبة
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- توليد المعرّفات الفريدة
CREATE EXTENSION IF NOT EXISTS "pg_trgm";     -- البحث التقريبي في الأسماء
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- ---------------------------------------------------------------------------
--  الأنواع المعدودة
-- ---------------------------------------------------------------------------

CREATE TYPE gender_enum AS ENUM ('ذكر', 'أنثى');
CREATE TYPE life_status_enum AS ENUM ('حي', 'متوفى', 'مفقود');
CREATE TYPE marital_status_enum AS ENUM ('أعزب', 'متزوج', 'مطلق', 'أرمل');
CREATE TYPE blood_type_enum AS ENUM ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-');
CREATE TYPE relation_type_enum AS ENUM ('أب', 'أم', 'ابن', 'ابنة', 'زوج', 'زوجة', 'أخ', 'أخت');
CREATE TYPE document_type_enum AS ENUM ('بطاقة وطنية', 'جواز سفر', 'شهادة جنسية', 'بطاقة عائلية');
CREATE TYPE document_status_enum AS ENUM ('سارية', 'منتهية', 'مفقودة', 'بدل فاقد', 'ملغاة');
CREATE TYPE request_type_enum AS ENUM ('إصدار', 'تعديل', 'بدل ضائع', 'تجديد', 'إلغاء');
CREATE TYPE request_status_enum AS ENUM ('مقدَّم', 'قيد المراجعة', 'مقبول', 'مرفوض', 'ملغى');
CREATE TYPE audit_action_enum AS ENUM ('إنشاء', 'قراءة', 'تعديل', 'حذف', 'اعتماد', 'دخول', 'خروج', 'محاولة فاشلة');

-- ---------------------------------------------------------------------------
--  الجداول والفهارس
-- ---------------------------------------------------------------------------

CREATE TABLE governorates (
	id SERIAL NOT NULL, 
	code VARCHAR(10) NOT NULL, 
	name_ar VARCHAR(100) NOT NULL, 
	name_en VARCHAR(100), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_governorates PRIMARY KEY (id), 
	CONSTRAINT uq_governorates_code UNIQUE (code), 
	CONSTRAINT uq_governorates_name_ar UNIQUE (name_ar)
);
CREATE INDEX ix_governorates_deleted_at ON governorates (deleted_at);

CREATE TABLE permissions (
	id SERIAL NOT NULL, 
	code VARCHAR(100) NOT NULL, 
	resource VARCHAR(50) NOT NULL, 
	action VARCHAR(30) NOT NULL, 
	name_ar VARCHAR(150) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_permissions PRIMARY KEY (id), 
	CONSTRAINT uq_permissions_code UNIQUE (code)
);

CREATE TABLE roles (
	id SERIAL NOT NULL, 
	code VARCHAR(50) NOT NULL, 
	name_ar VARCHAR(100) NOT NULL, 
	description_ar VARCHAR(500), 
	is_system BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_roles PRIMARY KEY (id), 
	CONSTRAINT uq_roles_code UNIQUE (code)
);
CREATE INDEX ix_roles_deleted_at ON roles (deleted_at);

CREATE TABLE districts (
	id SERIAL NOT NULL, 
	governorate_id INTEGER NOT NULL, 
	code VARCHAR(10) NOT NULL, 
	name_ar VARCHAR(100) NOT NULL, 
	name_en VARCHAR(100), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_districts PRIMARY KEY (id), 
	CONSTRAINT uq_district_code UNIQUE (governorate_id, code), 
	CONSTRAINT fk_districts_governorate_id_governorates FOREIGN KEY(governorate_id) REFERENCES governorates (id) ON DELETE RESTRICT
);
CREATE INDEX ix_districts_deleted_at ON districts (deleted_at);
CREATE INDEX ix_districts_governorate_id ON districts (governorate_id);

CREATE TABLE role_permissions (
	role_id INTEGER NOT NULL, 
	permission_id INTEGER NOT NULL, 
	granted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_role_permissions PRIMARY KEY (role_id, permission_id), 
	CONSTRAINT fk_role_permissions_role_id_roles FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE, 
	CONSTRAINT fk_role_permissions_permission_id_permissions FOREIGN KEY(permission_id) REFERENCES permissions (id) ON DELETE CASCADE
);

CREATE TABLE users (
	username VARCHAR(50) NOT NULL, 
	email VARCHAR(150), 
	password_hash VARCHAR(255) NOT NULL, 
	full_name_ar VARCHAR(200) NOT NULL, 
	phone VARCHAR(20), 
	governorate_id INTEGER, 
	is_active BOOLEAN NOT NULL, 
	must_change_password BOOLEAN NOT NULL, 
	totp_secret_encrypted VARCHAR(500), 
	totp_enabled BOOLEAN NOT NULL, 
	failed_login_attempts SMALLINT NOT NULL, 
	locked_until TIMESTAMP WITH TIME ZONE, 
	last_login_at TIMESTAMP WITH TIME ZONE, 
	password_changed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	created_by UUID, 
	updated_by UUID, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_users PRIMARY KEY (id), 
	CONSTRAINT ck_users_failed_attempts CHECK (failed_login_attempts >= 0), 
	CONSTRAINT uq_users_username UNIQUE (username), 
	CONSTRAINT uq_users_email UNIQUE (email), 
	CONSTRAINT fk_users_governorate_id_governorates FOREIGN KEY(governorate_id) REFERENCES governorates (id), 
	CONSTRAINT fk_users_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_users_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id)
);
CREATE INDEX ix_users_deleted_at ON users (deleted_at);

CREATE TABLE audit_log (
	id BIGSERIAL NOT NULL, 
	user_id UUID, 
	username VARCHAR(50), 
	action audit_action_enum NOT NULL, 
	resource_type VARCHAR(50) NOT NULL, 
	resource_id VARCHAR(50), 
	old_values JSONB, 
	new_values JSONB, 
	ip_address INET, 
	user_agent VARCHAR(300), 
	request_path VARCHAR(300), 
	succeeded BOOLEAN NOT NULL, 
	error_message TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_audit_log PRIMARY KEY (id), 
	CONSTRAINT fk_audit_log_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX idx_audit_created ON audit_log (created_at);
CREATE INDEX idx_audit_resource ON audit_log (resource_type, resource_id);
CREATE INDEX ix_audit_log_action ON audit_log (action);
CREATE INDEX ix_audit_log_user_id ON audit_log (user_id);

CREATE TABLE persons (
	national_id VARCHAR(12) NOT NULL, 
	first_name VARCHAR(50) NOT NULL, 
	father_name VARCHAR(50) NOT NULL, 
	grandfather_name VARCHAR(50) NOT NULL, 
	family_name VARCHAR(50) NOT NULL, 
	mother_full_name VARCHAR(150) NOT NULL, 
	full_name_normalized VARCHAR(300), 
	birth_date DATE NOT NULL, 
	birth_date_hijri VARCHAR(12), 
	birth_governorate_id INTEGER, 
	birth_place_detail VARCHAR(200), 
	gender gender_enum NOT NULL, 
	nationality VARCHAR(60) NOT NULL, 
	religion VARCHAR(50), 
	blood_type blood_type_enum, 
	marital_status marital_status_enum NOT NULL, 
	occupation VARCHAR(100), 
	education_level VARCHAR(100), 
	life_status life_status_enum NOT NULL, 
	photo_path VARCHAR(300), 
	fingerprint_path VARCHAR(300), 
	notes TEXT, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_by UUID, 
	updated_by UUID, 
	CONSTRAINT pk_persons PRIMARY KEY (id), 
	CONSTRAINT ck_persons_national_id_length CHECK (length(national_id) = 12), 
	CONSTRAINT fk_persons_birth_governorate_id_governorates FOREIGN KEY(birth_governorate_id) REFERENCES governorates (id), 
	CONSTRAINT fk_persons_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_persons_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id)
);
CREATE INDEX ix_persons_birth_date ON persons (birth_date);
CREATE INDEX ix_persons_deleted_at ON persons (deleted_at);
CREATE INDEX ix_persons_full_name_normalized ON persons (full_name_normalized);
CREATE INDEX ix_persons_life_status ON persons (life_status);
CREATE INDEX ix_persons_name_trgm ON persons USING gin (full_name_normalized gin_trgm_ops);
CREATE UNIQUE INDEX ix_persons_national_id ON persons (national_id);

CREATE TABLE refresh_tokens (
	user_id UUID NOT NULL, 
	token_hash VARCHAR(255) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	user_agent VARCHAR(300), 
	ip_address INET, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_refresh_tokens PRIMARY KEY (id), 
	CONSTRAINT fk_refresh_tokens_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT uq_refresh_tokens_token_hash UNIQUE (token_hash)
);
CREATE INDEX ix_refresh_tokens_expires_at ON refresh_tokens (expires_at);
CREATE INDEX ix_refresh_tokens_user_id ON refresh_tokens (user_id);

CREATE TABLE subdistricts (
	id SERIAL NOT NULL, 
	district_id INTEGER NOT NULL, 
	code VARCHAR(10) NOT NULL, 
	name_ar VARCHAR(100) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_subdistricts PRIMARY KEY (id), 
	CONSTRAINT uq_subdistrict_code UNIQUE (district_id, code), 
	CONSTRAINT fk_subdistricts_district_id_districts FOREIGN KEY(district_id) REFERENCES districts (id) ON DELETE RESTRICT
);
CREATE INDEX ix_subdistricts_deleted_at ON subdistricts (deleted_at);
CREATE INDEX ix_subdistricts_district_id ON subdistricts (district_id);

CREATE TABLE user_roles (
	user_id UUID NOT NULL, 
	role_id INTEGER NOT NULL, 
	assigned_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	assigned_by UUID, 
	CONSTRAINT pk_user_roles PRIMARY KEY (user_id, role_id), 
	CONSTRAINT fk_user_roles_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT fk_user_roles_role_id_roles FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_user_roles_assigned_by_users FOREIGN KEY(assigned_by) REFERENCES users (id)
);

CREATE TABLE addresses (
	person_id UUID NOT NULL, 
	governorate_id INTEGER NOT NULL, 
	district_id INTEGER, 
	subdistrict_id INTEGER, 
	quarter VARCHAR(100), 
	street VARCHAR(100), 
	house_number VARCHAR(20), 
	postal_code VARCHAR(10), 
	details TEXT, 
	valid_from DATE NOT NULL, 
	valid_to DATE, 
	is_current BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_by UUID, 
	updated_by UUID, 
	CONSTRAINT pk_addresses PRIMARY KEY (id), 
	CONSTRAINT ck_addresses_address_period CHECK (valid_to IS NULL OR valid_to >= valid_from), 
	CONSTRAINT fk_addresses_person_id_persons FOREIGN KEY(person_id) REFERENCES persons (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_addresses_governorate_id_governorates FOREIGN KEY(governorate_id) REFERENCES governorates (id), 
	CONSTRAINT fk_addresses_district_id_districts FOREIGN KEY(district_id) REFERENCES districts (id), 
	CONSTRAINT fk_addresses_subdistrict_id_subdistricts FOREIGN KEY(subdistrict_id) REFERENCES subdistricts (id), 
	CONSTRAINT fk_addresses_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_addresses_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id)
);
CREATE INDEX ix_addresses_deleted_at ON addresses (deleted_at);
CREATE INDEX ix_addresses_governorate_id ON addresses (governorate_id);
CREATE INDEX ix_addresses_person_id ON addresses (person_id);
CREATE UNIQUE INDEX uq_address_current ON addresses (person_id) WHERE is_current AND deleted_at IS NULL;

CREATE TABLE birth_records (
	record_number VARCHAR(20) NOT NULL, 
	person_id UUID NOT NULL, 
	father_id UUID, 
	mother_id UUID, 
	birth_date DATE NOT NULL, 
	birth_time TIME WITHOUT TIME ZONE, 
	hospital_name VARCHAR(200), 
	governorate_id INTEGER NOT NULL, 
	birth_weight_grams INTEGER, 
	delivery_type VARCHAR(50), 
	attending_physician VARCHAR(150), 
	informant_name VARCHAR(200), 
	informant_relation VARCHAR(50), 
	registration_date DATE NOT NULL, 
	registration_office VARCHAR(150), 
	certificate_issued BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_by UUID, 
	updated_by UUID, 
	CONSTRAINT pk_birth_records PRIMARY KEY (id), 
	CONSTRAINT ck_birth_records_birth_weight CHECK (birth_weight_grams IS NULL OR (birth_weight_grams >= 200 AND birth_weight_grams <= 8000)), 
	CONSTRAINT ck_birth_records_birth_reg CHECK (registration_date >= birth_date), 
	CONSTRAINT ck_birth_records_parents_differ CHECK (father_id IS NULL OR mother_id IS NULL OR father_id <> mother_id), 
	CONSTRAINT uq_birth_records_record_number UNIQUE (record_number), 
	CONSTRAINT uq_birth_records_person_id UNIQUE (person_id), 
	CONSTRAINT fk_birth_records_person_id_persons FOREIGN KEY(person_id) REFERENCES persons (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_birth_records_father_id_persons FOREIGN KEY(father_id) REFERENCES persons (id), 
	CONSTRAINT fk_birth_records_mother_id_persons FOREIGN KEY(mother_id) REFERENCES persons (id), 
	CONSTRAINT fk_birth_records_governorate_id_governorates FOREIGN KEY(governorate_id) REFERENCES governorates (id), 
	CONSTRAINT fk_birth_records_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_birth_records_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id)
);
CREATE INDEX ix_birth_records_birth_date ON birth_records (birth_date);
CREATE INDEX ix_birth_records_deleted_at ON birth_records (deleted_at);
CREATE INDEX ix_birth_records_father_id ON birth_records (father_id);
CREATE INDEX ix_birth_records_governorate_id ON birth_records (governorate_id);
CREATE INDEX ix_birth_records_mother_id ON birth_records (mother_id);

CREATE TABLE death_records (
	record_number VARCHAR(20) NOT NULL, 
	person_id UUID NOT NULL, 
	death_date DATE NOT NULL, 
	death_time TIME WITHOUT TIME ZONE, 
	death_place VARCHAR(200), 
	governorate_id INTEGER NOT NULL, 
	cause_of_death VARCHAR(300), 
	cause_category VARCHAR(100), 
	reporting_authority VARCHAR(200), 
	certifying_physician VARCHAR(150), 
	burial_place VARCHAR(200), 
	registration_date DATE NOT NULL, 
	certificate_issued BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_by UUID, 
	updated_by UUID, 
	CONSTRAINT pk_death_records PRIMARY KEY (id), 
	CONSTRAINT ck_death_records_death_reg CHECK (registration_date >= death_date), 
	CONSTRAINT uq_death_records_record_number UNIQUE (record_number), 
	CONSTRAINT uq_death_records_person_id UNIQUE (person_id), 
	CONSTRAINT fk_death_records_person_id_persons FOREIGN KEY(person_id) REFERENCES persons (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_death_records_governorate_id_governorates FOREIGN KEY(governorate_id) REFERENCES governorates (id), 
	CONSTRAINT fk_death_records_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_death_records_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id)
);
CREATE INDEX ix_death_records_death_date ON death_records (death_date);
CREATE INDEX ix_death_records_deleted_at ON death_records (deleted_at);
CREATE INDEX ix_death_records_governorate_id ON death_records (governorate_id);

CREATE TABLE documents (
	person_id UUID NOT NULL, 
	document_type document_type_enum NOT NULL, 
	document_number VARCHAR(30) NOT NULL, 
	issue_date DATE NOT NULL, 
	expiry_date DATE, 
	issuing_authority VARCHAR(200) NOT NULL, 
	issuing_governorate_id INTEGER, 
	status document_status_enum NOT NULL, 
	replaces_document_id UUID, 
	scan_path VARCHAR(300), 
	notes TEXT, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_by UUID, 
	updated_by UUID, 
	CONSTRAINT pk_documents PRIMARY KEY (id), 
	CONSTRAINT uq_document UNIQUE (document_type, document_number), 
	CONSTRAINT ck_documents_document_dates CHECK (expiry_date IS NULL OR expiry_date > issue_date), 
	CONSTRAINT fk_documents_person_id_persons FOREIGN KEY(person_id) REFERENCES persons (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_documents_issuing_governorate_id_governorates FOREIGN KEY(issuing_governorate_id) REFERENCES governorates (id), 
	CONSTRAINT fk_documents_replaces_document_id_documents FOREIGN KEY(replaces_document_id) REFERENCES documents (id), 
	CONSTRAINT fk_documents_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_documents_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id)
);
CREATE INDEX ix_documents_deleted_at ON documents (deleted_at);
CREATE INDEX ix_documents_document_number ON documents (document_number);
CREATE INDEX ix_documents_expiry_date ON documents (expiry_date);
CREATE INDEX ix_documents_person_id ON documents (person_id);
CREATE UNIQUE INDEX uq_active_document_per_type ON documents (person_id, document_type) WHERE status = 'سارية' AND deleted_at IS NULL;

CREATE TABLE family_cards (
	card_number VARCHAR(20) NOT NULL, 
	head_person_id UUID NOT NULL, 
	governorate_id INTEGER NOT NULL, 
	issue_date DATE NOT NULL, 
	issuing_office VARCHAR(150), 
	is_active BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_by UUID, 
	updated_by UUID, 
	CONSTRAINT pk_family_cards PRIMARY KEY (id), 
	CONSTRAINT uq_family_cards_card_number UNIQUE (card_number), 
	CONSTRAINT fk_family_cards_head_person_id_persons FOREIGN KEY(head_person_id) REFERENCES persons (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_family_cards_governorate_id_governorates FOREIGN KEY(governorate_id) REFERENCES governorates (id), 
	CONSTRAINT fk_family_cards_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_family_cards_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id)
);
CREATE INDEX ix_family_cards_deleted_at ON family_cards (deleted_at);
CREATE INDEX ix_family_cards_head_person_id ON family_cards (head_person_id);

CREATE TABLE family_relations (
	person_id UUID NOT NULL, 
	related_person_id UUID NOT NULL, 
	relation_type relation_type_enum NOT NULL, 
	start_date DATE, 
	end_date DATE, 
	is_active BOOLEAN NOT NULL, 
	created_by UUID, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_family_relations PRIMARY KEY (id), 
	CONSTRAINT ck_family_relations_no_self_relation CHECK (person_id <> related_person_id), 
	CONSTRAINT ck_family_relations_relation_period CHECK (end_date IS NULL OR end_date >= start_date), 
	CONSTRAINT uq_relation UNIQUE (person_id, related_person_id, relation_type), 
	CONSTRAINT fk_family_relations_person_id_persons FOREIGN KEY(person_id) REFERENCES persons (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_family_relations_related_person_id_persons FOREIGN KEY(related_person_id) REFERENCES persons (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_family_relations_created_by_users FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE INDEX ix_family_relations_deleted_at ON family_relations (deleted_at);
CREATE INDEX ix_family_relations_person_id ON family_relations (person_id);
CREATE INDEX ix_family_relations_related_person_id ON family_relations (related_person_id);

CREATE TABLE marriage_contracts (
	contract_number VARCHAR(20) NOT NULL, 
	husband_id UUID NOT NULL, 
	wife_id UUID NOT NULL, 
	contract_date DATE NOT NULL, 
	contract_date_hijri VARCHAR(12), 
	governorate_id INTEGER NOT NULL, 
	court_name VARCHAR(200), 
	officiant_name VARCHAR(150) NOT NULL, 
	witness1_name VARCHAR(150) NOT NULL, 
	witness1_national_id VARCHAR(12), 
	witness2_name VARCHAR(150) NOT NULL, 
	witness2_national_id VARCHAR(12), 
	dowry_prompt NUMERIC(14, 2), 
	dowry_deferred NUMERIC(14, 2), 
	currency VARCHAR(10) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	document_issued BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_by UUID, 
	updated_by UUID, 
	CONSTRAINT pk_marriage_contracts PRIMARY KEY (id), 
	CONSTRAINT ck_marriage_contracts_spouses_differ CHECK (husband_id <> wife_id), 
	CONSTRAINT ck_marriage_contracts_dowry_positive CHECK ((dowry_prompt IS NULL OR dowry_prompt >= 0) AND (dowry_deferred IS NULL OR dowry_deferred >= 0)), 
	CONSTRAINT uq_marriage_contracts_contract_number UNIQUE (contract_number), 
	CONSTRAINT fk_marriage_contracts_husband_id_persons FOREIGN KEY(husband_id) REFERENCES persons (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_marriage_contracts_wife_id_persons FOREIGN KEY(wife_id) REFERENCES persons (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_marriage_contracts_governorate_id_governorates FOREIGN KEY(governorate_id) REFERENCES governorates (id), 
	CONSTRAINT fk_marriage_contracts_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_marriage_contracts_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id)
);
CREATE INDEX ix_marriage_contracts_contract_date ON marriage_contracts (contract_date);
CREATE INDEX ix_marriage_contracts_deleted_at ON marriage_contracts (deleted_at);
CREATE INDEX ix_marriage_contracts_husband_id ON marriage_contracts (husband_id);
CREATE INDEX ix_marriage_contracts_wife_id ON marriage_contracts (wife_id);

CREATE TABLE service_requests (
	reference_number VARCHAR(25) NOT NULL, 
	person_id UUID NOT NULL, 
	request_type request_type_enum NOT NULL, 
	subject VARCHAR(200) NOT NULL, 
	details TEXT, 
	status request_status_enum NOT NULL, 
	submitted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	submitted_by UUID, 
	reviewed_at TIMESTAMP WITH TIME ZONE, 
	reviewed_by UUID, 
	decision_at TIMESTAMP WITH TIME ZONE, 
	decision_by UUID, 
	rejection_reason TEXT, 
	fee_amount NUMERIC(12, 2) NOT NULL, 
	fee_paid BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_service_requests PRIMARY KEY (id), 
	CONSTRAINT ck_service_requests_fee_positive CHECK (fee_amount >= 0), 
	CONSTRAINT ck_service_requests_rejection_reason CHECK (status <> 'مرفوض' OR rejection_reason IS NOT NULL), 
	CONSTRAINT fk_service_requests_person_id_persons FOREIGN KEY(person_id) REFERENCES persons (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_service_requests_submitted_by_users FOREIGN KEY(submitted_by) REFERENCES users (id), 
	CONSTRAINT fk_service_requests_reviewed_by_users FOREIGN KEY(reviewed_by) REFERENCES users (id), 
	CONSTRAINT fk_service_requests_decision_by_users FOREIGN KEY(decision_by) REFERENCES users (id)
);
CREATE INDEX ix_service_requests_deleted_at ON service_requests (deleted_at);
CREATE INDEX ix_service_requests_person_id ON service_requests (person_id);
CREATE UNIQUE INDEX ix_service_requests_reference_number ON service_requests (reference_number);
CREATE INDEX ix_service_requests_status ON service_requests (status);

CREATE TABLE divorce_records (
	record_number VARCHAR(20) NOT NULL, 
	marriage_id UUID NOT NULL, 
	divorce_date DATE NOT NULL, 
	divorce_date_hijri VARCHAR(12), 
	divorce_type VARCHAR(50), 
	court_name VARCHAR(200), 
	judge_name VARCHAR(150), 
	reason TEXT, 
	custody_notes TEXT, 
	document_issued BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_by UUID, 
	updated_by UUID, 
	CONSTRAINT pk_divorce_records PRIMARY KEY (id), 
	CONSTRAINT uq_divorce_records_record_number UNIQUE (record_number), 
	CONSTRAINT fk_divorce_records_marriage_id_marriage_contracts FOREIGN KEY(marriage_id) REFERENCES marriage_contracts (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_divorce_records_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_divorce_records_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id)
);
CREATE INDEX ix_divorce_records_deleted_at ON divorce_records (deleted_at);
CREATE INDEX ix_divorce_records_divorce_date ON divorce_records (divorce_date);
CREATE INDEX ix_divorce_records_marriage_id ON divorce_records (marriage_id);

CREATE TABLE family_card_members (
	family_card_id UUID NOT NULL, 
	person_id UUID NOT NULL, 
	relation_to_head relation_type_enum NOT NULL, 
	added_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	removed_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	CONSTRAINT pk_family_card_members PRIMARY KEY (id), 
	CONSTRAINT uq_card_member UNIQUE (family_card_id, person_id), 
	CONSTRAINT fk_family_card_members_family_card_id_family_cards FOREIGN KEY(family_card_id) REFERENCES family_cards (id) ON DELETE CASCADE, 
	CONSTRAINT fk_family_card_members_person_id_persons FOREIGN KEY(person_id) REFERENCES persons (id) ON DELETE RESTRICT
);
CREATE INDEX ix_family_card_members_family_card_id ON family_card_members (family_card_id);
CREATE INDEX ix_family_card_members_person_id ON family_card_members (person_id);
CREATE UNIQUE INDEX uq_person_active_card ON family_card_members (person_id) WHERE removed_at IS NULL;

CREATE TABLE request_attachments (
	request_id UUID NOT NULL, 
	file_name VARCHAR(255) NOT NULL, 
	file_path VARCHAR(300) NOT NULL, 
	mime_type VARCHAR(100), 
	file_size_bytes BIGINT, 
	uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	uploaded_by UUID, 
	id UUID NOT NULL, 
	CONSTRAINT pk_request_attachments PRIMARY KEY (id), 
	CONSTRAINT fk_request_attachments_request_id_service_requests FOREIGN KEY(request_id) REFERENCES service_requests (id) ON DELETE CASCADE, 
	CONSTRAINT fk_request_attachments_uploaded_by_users FOREIGN KEY(uploaded_by) REFERENCES users (id)
);
CREATE INDEX ix_request_attachments_request_id ON request_attachments (request_id);

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

COMMIT;

-- =============================================================================
--  نهاية المخطط
-- =============================================================================
