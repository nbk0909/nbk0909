/* =============================================================
   برنامج تفتيش السلامة المهنية - سكربت إنشاء قاعدة البيانات
   Occupational Safety Inspection Program - Database Script
   SQL Server 2014+
   ============================================================= */

USE master;
GO

IF DB_ID('SafetyInspectionDB') IS NULL
BEGIN
    CREATE DATABASE SafetyInspectionDB
    COLLATE Arabic_CI_AS;
END
GO

USE SafetyInspectionDB;
GO

/* ===================== المستخدمون ===================== */
IF OBJECT_ID('dbo.Users', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.Users (
        UserId          INT IDENTITY(1,1) PRIMARY KEY,
        Username        NVARCHAR(50)  NOT NULL UNIQUE,
        PasswordHash    NVARCHAR(256) NOT NULL,
        FullName        NVARCHAR(150) NOT NULL,
        Role            NVARCHAR(20)  NOT NULL DEFAULT N'مفتش',
        IsActive        BIT           NOT NULL DEFAULT 1,
        CreatedAt       DATETIME      NOT NULL DEFAULT GETDATE(),
        LastLogin       DATETIME      NULL
    );
END
GO

/* ===================== المنشآت ===================== */
IF OBJECT_ID('dbo.Establishments', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.Establishments (
        EstablishmentId   INT IDENTITY(1,1) PRIMARY KEY,
        EstablishmentName NVARCHAR(200) NOT NULL,
        RegistrationNo    NVARCHAR(50)  NULL,
        Sector            NVARCHAR(100) NULL,
        ActivityType      NVARCHAR(150) NULL,
        Address           NVARCHAR(300) NULL,
        City              NVARCHAR(100) NULL,
        Phone             NVARCHAR(20)  NULL,
        Email             NVARCHAR(150) NULL,
        OwnerName         NVARCHAR(150) NULL,
        EmployeesCount    INT           NOT NULL DEFAULT 0,
        RiskLevel         NVARCHAR(20)  NOT NULL DEFAULT N'متوسط',
        CreatedAt         DATETIME      NOT NULL DEFAULT GETDATE()
    );
END
GO

/* ===================== المفتشون ===================== */
IF OBJECT_ID('dbo.Inspectors', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.Inspectors (
        InspectorId    INT IDENTITY(1,1) PRIMARY KEY,
        EmployeeNo     NVARCHAR(20)  NOT NULL UNIQUE,
        FullName       NVARCHAR(150) NOT NULL,
        NationalId     NVARCHAR(20)  NULL,
        Specialization NVARCHAR(100) NULL,
        Phone          NVARCHAR(20)  NULL,
        Email          NVARCHAR(150) NULL,
        HireDate       DATE          NULL,
        IsActive       BIT           NOT NULL DEFAULT 1,
        CreatedAt      DATETIME      NOT NULL DEFAULT GETDATE()
    );
END
GO

/* ===================== بنود قائمة الفحص ===================== */
IF OBJECT_ID('dbo.ChecklistItems', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.ChecklistItems (
        ItemId      INT IDENTITY(1,1) PRIMARY KEY,
        Category    NVARCHAR(100) NOT NULL,
        ItemText    NVARCHAR(300) NOT NULL,
        IsCritical  BIT           NOT NULL DEFAULT 0,
        IsActive    BIT           NOT NULL DEFAULT 1
    );
END
GO

/* ===================== التفتيشات ===================== */
IF OBJECT_ID('dbo.Inspections', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.Inspections (
        InspectionId    INT IDENTITY(1,1) PRIMARY KEY,
        EstablishmentId INT          NOT NULL,
        InspectorId     INT          NOT NULL,
        InspectionDate  DATE         NOT NULL,
        InspectionType  NVARCHAR(50) NOT NULL DEFAULT N'دوري',
        Status          NVARCHAR(30) NOT NULL DEFAULT N'مفتوح',
        OverallRating   NVARCHAR(20) NULL,
        Notes           NVARCHAR(MAX) NULL,
        CreatedAt       DATETIME     NOT NULL DEFAULT GETDATE(),
        CONSTRAINT FK_Inspections_Establishment
            FOREIGN KEY (EstablishmentId) REFERENCES dbo.Establishments(EstablishmentId),
        CONSTRAINT FK_Inspections_Inspector
            FOREIGN KEY (InspectorId)    REFERENCES dbo.Inspectors(InspectorId)
    );
END
GO

/* ===================== المخالفات ===================== */
IF OBJECT_ID('dbo.Violations', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.Violations (
        ViolationId   INT IDENTITY(1,1) PRIMARY KEY,
        InspectionId  INT           NOT NULL,
        ViolationType NVARCHAR(100) NOT NULL,
        Description   NVARCHAR(500) NOT NULL,
        Severity      NVARCHAR(20)  NOT NULL DEFAULT N'متوسطة',
        FineAmount    DECIMAL(12,2) NOT NULL DEFAULT 0,
        Status        NVARCHAR(30)  NOT NULL DEFAULT N'قائمة',
        CorrectionDeadline DATE     NULL,
        CreatedAt     DATETIME      NOT NULL DEFAULT GETDATE(),
        CONSTRAINT FK_Violations_Inspection
            FOREIGN KEY (InspectionId) REFERENCES dbo.Inspections(InspectionId) ON DELETE CASCADE
    );
END
GO

/* ===================== نتائج بنود الفحص لكل تفتيش ===================== */
IF OBJECT_ID('dbo.InspectionChecklist', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.InspectionChecklist (
        Id            INT IDENTITY(1,1) PRIMARY KEY,
        InspectionId  INT          NOT NULL,
        ItemId        INT          NOT NULL,
        Result        NVARCHAR(20) NOT NULL DEFAULT N'مطابق',
        Notes         NVARCHAR(300) NULL,
        CONSTRAINT FK_IC_Inspection FOREIGN KEY (InspectionId) REFERENCES dbo.Inspections(InspectionId) ON DELETE CASCADE,
        CONSTRAINT FK_IC_Item        FOREIGN KEY (ItemId)       REFERENCES dbo.ChecklistItems(ItemId)
    );
END
GO

/* ===================== بيانات افتراضية ===================== */

-- مستخدم النظام الافتراضي (admin / admin123)
-- كلمة المرور هنا مخزنة كنص بسيط للتجربة - يتم استبدالها بـ hash من البرنامج عند التشغيل
IF NOT EXISTS (SELECT 1 FROM dbo.Users WHERE Username = N'admin')
BEGIN
    INSERT INTO dbo.Users (Username, PasswordHash, FullName, Role)
    VALUES (N'admin',
            N'240BE518FABD2724DDB6F04EEB1DA5967448D7E831C08C8FA822809F74C720A9', -- SHA256("admin123")
            N'مدير النظام',
            N'مدير');
END
GO

-- بنود قائمة الفحص الافتراضية
IF NOT EXISTS (SELECT 1 FROM dbo.ChecklistItems)
BEGIN
    INSERT INTO dbo.ChecklistItems (Category, ItemText, IsCritical) VALUES
    (N'الحماية من الحريق', N'توفر طفايات الحريق صالحة للاستخدام',                    1),
    (N'الحماية من الحريق', N'توفر مخارج طوارئ واضحة وغير مغلقة',                     1),
    (N'الحماية من الحريق', N'توفر نظام إنذار حريق يعمل بكفاءة',                      1),
    (N'الحماية من الحريق', N'وجود لوحات إرشادية لمسارات الإخلاء',                     0),
    (N'معدات الوقاية الشخصية', N'توفر الخوذات الواقية للعاملين',                     1),
    (N'معدات الوقاية الشخصية', N'توفر الأحذية الواقية المناسبة',                      1),
    (N'معدات الوقاية الشخصية', N'توفر النظارات والقفازات الواقية',                    0),
    (N'الكهرباء',           N'سلامة التوصيلات الكهربائية وعدم وجود أسلاك مكشوفة',     1),
    (N'الكهرباء',           N'وجود لوحات تحكم كهربائية مؤمنة',                         1),
    (N'الكهرباء',           N'توفر التأريض الكهربائي السليم',                           1),
    (N'بيئة العمل',          N'نظافة مكان العمل وترتيبه',                              0),
    (N'بيئة العمل',          N'التهوية الجيدة في أماكن العمل',                         0),
    (N'بيئة العمل',          N'الإضاءة المناسبة في كافة مناطق العمل',                  0),
    (N'الإسعافات الأولية',    N'توفر صندوق إسعافات أولية مجهز',                         1),
    (N'الإسعافات الأولية',    N'وجود عاملين مدربين على الإسعافات الأولية',               0),
    (N'المواد الكيميائية',    N'تخزين المواد الكيميائية بطريقة آمنة',                   1),
    (N'المواد الكيميائية',    N'وجود نشرات السلامة للمواد الكيميائية (MSDS)',           0),
    (N'الآلات والمعدات',      N'وجود حواجز حماية على الأجزاء المتحركة',                 1),
    (N'الآلات والمعدات',      N'صيانة دورية موثقة للآلات والمعدات',                    0),
    (N'التدريب والتوعية',     N'توفر سجل تدريب العاملين على السلامة',                   0);
END
GO

PRINT N'تم إنشاء قاعدة بيانات SafetyInspectionDB بنجاح';
GO
