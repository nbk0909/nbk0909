Imports System.Data
Imports System.Data.SqlClient

''' <summary>
''' شاشة إدارة المخالفات - يمكن فتحها لتفتيش معين أو لكل المخالفات
''' </summary>
Public Class FrmViolations

    Private _currentId As Integer = 0
    Private _filterInspectionId As Integer = 0

    ''' <summary>الإنشاء بدون تفتيش محدد - عرض جميع المخالفات</summary>
    Public Sub New()
        InitializeComponent()
    End Sub

    ''' <summary>الإنشاء مع تفتيش محدد للتصفية</summary>
    Public Sub New(inspectionId As Integer)
        InitializeComponent()
        _filterInspectionId = inspectionId
    End Sub

    Private Sub FrmViolations_Load(sender As Object, e As EventArgs) Handles MyBase.Load
        LoadInspections()
        If _filterInspectionId > 0 Then
            cmbFilterInsp.SelectedValue = _filterInspectionId
            cmbInspection.SelectedValue = _filterInspectionId
        End If
        LoadGrid()
        ClearForm()
    End Sub

    Private Sub LoadInspections()
        Try
            Dim sql = "SELECT i.InspectionId,
                              CAST(i.InspectionId AS NVARCHAR) + ' - ' +
                              e.EstablishmentName + ' (' +
                              CONVERT(NVARCHAR, i.InspectionDate, 23) + ')' AS DisplayName
                       FROM dbo.Inspections i
                       INNER JOIN dbo.Establishments e ON e.EstablishmentId = i.EstablishmentId
                       ORDER BY i.InspectionDate DESC"
            Dim dt = DatabaseHelper.ExecuteQuery(sql)

            ' إضافة خيار "الكل" لعنصر التصفية
            Dim filterDt = dt.Copy()
            Dim allRow = filterDt.NewRow()
            allRow("InspectionId") = 0
            allRow("DisplayName") = "-- جميع التفتيشات --"
            filterDt.Rows.InsertAt(allRow, 0)

            cmbFilterInsp.DataSource = filterDt
            cmbFilterInsp.DisplayMember = "DisplayName"
            cmbFilterInsp.ValueMember = "InspectionId"
            cmbFilterInsp.SelectedIndex = 0

            cmbInspection.DataSource = dt
            cmbInspection.DisplayMember = "DisplayName"
            cmbInspection.ValueMember = "InspectionId"
            cmbInspection.SelectedIndex = -1
        Catch ex As Exception
            MessageBox.Show("خطأ في تحميل التفتيشات: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub LoadGrid()
        Try
            Dim filterId As Integer = 0
            If cmbFilterInsp.SelectedValue IsNot Nothing AndAlso IsNumeric(cmbFilterInsp.SelectedValue) Then
                filterId = CInt(cmbFilterInsp.SelectedValue)
            End If

            Dim sql = "SELECT v.ViolationId AS [الرقم],
                              v.InspectionId AS [رقم التفتيش],
                              e.EstablishmentName AS [المنشأة],
                              v.ViolationType AS [نوع المخالفة],
                              v.Description AS [الوصف],
                              v.Severity AS [درجة الخطورة],
                              v.FineAmount AS [الغرامة],
                              v.Status AS [الحالة],
                              v.CorrectionDeadline AS [تاريخ التصحيح]
                       FROM dbo.Violations v
                       INNER JOIN dbo.Inspections i ON i.InspectionId = v.InspectionId
                       INNER JOIN dbo.Establishments e ON e.EstablishmentId = i.EstablishmentId
                       WHERE (@id = 0 OR v.InspectionId = @id)
                       ORDER BY v.ViolationId DESC"
            grdViolations.DataSource = DatabaseHelper.ExecuteQuery(sql,
                New SqlParameter("@id", filterId))
        Catch ex As Exception
            MessageBox.Show("خطأ في تحميل البيانات: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub ClearForm()
        _currentId = 0
        cmbType.SelectedIndex = -1
        txtDesc.Clear()
        cmbSeverity.SelectedIndex = 1
        numFine.Value = 0
        cmbStatus.SelectedIndex = 0
        dtpDeadline.Value = DateTime.Today.AddDays(30)
        If _filterInspectionId > 0 Then
            cmbInspection.SelectedValue = _filterInspectionId
        Else
            cmbInspection.SelectedIndex = -1
        End If
    End Sub

    Private Sub btnNew_Click(sender As Object, e As EventArgs) Handles btnNew.Click
        ClearForm()
    End Sub

    Private Sub btnRefresh_Click(sender As Object, e As EventArgs) Handles btnRefresh.Click
        LoadInspections()
        LoadGrid()
    End Sub

    Private Sub cmbFilterInsp_SelectedIndexChanged(sender As Object, e As EventArgs) Handles cmbFilterInsp.SelectedIndexChanged
        LoadGrid()
    End Sub

    Private Sub btnSave_Click(sender As Object, e As EventArgs) Handles btnSave.Click
        If cmbInspection.SelectedValue Is Nothing OrElse
           String.IsNullOrEmpty(cmbType.Text) OrElse
           String.IsNullOrWhiteSpace(txtDesc.Text) Then
            MessageBox.Show("الرجاء تعبئة الحقول المطلوبة (التفتيش، نوع المخالفة، الوصف).",
                            "تنبيه", MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If

        Try
            Dim params As New List(Of SqlParameter) From {
                New SqlParameter("@insp", CInt(cmbInspection.SelectedValue)),
                New SqlParameter("@type", cmbType.Text),
                New SqlParameter("@desc", txtDesc.Text.Trim()),
                New SqlParameter("@sev", cmbSeverity.Text),
                New SqlParameter("@fine", numFine.Value),
                New SqlParameter("@status", cmbStatus.Text),
                New SqlParameter("@deadline", dtpDeadline.Value.Date)
            }

            Dim sql As String
            If _currentId = 0 Then
                sql = "INSERT INTO dbo.Violations
                       (InspectionId, ViolationType, Description, Severity, FineAmount, Status, CorrectionDeadline)
                       VALUES (@insp, @type, @desc, @sev, @fine, @status, @deadline)"
            Else
                sql = "UPDATE dbo.Violations SET
                          InspectionId=@insp, ViolationType=@type, Description=@desc,
                          Severity=@sev, FineAmount=@fine, Status=@status,
                          CorrectionDeadline=@deadline
                       WHERE ViolationId=@id"
                params.Add(New SqlParameter("@id", _currentId))
            End If

            DatabaseHelper.ExecuteNonQuery(sql, params.ToArray())
            MessageBox.Show("تم حفظ المخالفة بنجاح.", "نجاح",
                            MessageBoxButtons.OK, MessageBoxIcon.Information)
            LoadGrid()
            ClearForm()
        Catch ex As Exception
            MessageBox.Show("خطأ في حفظ البيانات: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub btnDelete_Click(sender As Object, e As EventArgs) Handles btnDelete.Click
        If _currentId = 0 Then
            MessageBox.Show("الرجاء اختيار مخالفة من القائمة.", "تنبيه",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If
        If MessageBox.Show("هل تريد بالتأكيد حذف هذه المخالفة؟", "تأكيد الحذف",
                           MessageBoxButtons.YesNo, MessageBoxIcon.Question) <> DialogResult.Yes Then
            Return
        End If
        Try
            DatabaseHelper.ExecuteNonQuery(
                "DELETE FROM dbo.Violations WHERE ViolationId=@id",
                New SqlParameter("@id", _currentId))
            MessageBox.Show("تم الحذف بنجاح.", "نجاح",
                            MessageBoxButtons.OK, MessageBoxIcon.Information)
            LoadGrid()
            ClearForm()
        Catch ex As Exception
            MessageBox.Show("خطأ في الحذف: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub grdViolations_CellClick(sender As Object, e As DataGridViewCellEventArgs) Handles grdViolations.CellClick
        If e.RowIndex < 0 Then Return
        _currentId = CInt(grdViolations.Rows(e.RowIndex).Cells("الرقم").Value)
        Try
            Dim dt = DatabaseHelper.ExecuteQuery(
                "SELECT * FROM dbo.Violations WHERE ViolationId=@id",
                New SqlParameter("@id", _currentId))
            If dt.Rows.Count = 0 Then Return
            Dim r = dt.Rows(0)
            cmbInspection.SelectedValue = CInt(r("InspectionId"))
            cmbType.Text = r("ViolationType").ToString()
            txtDesc.Text = r("Description").ToString()
            cmbSeverity.Text = r("Severity").ToString()
            numFine.Value = CDec(r("FineAmount"))
            cmbStatus.Text = r("Status").ToString()
            If Not IsDBNull(r("CorrectionDeadline")) Then
                dtpDeadline.Value = CDate(r("CorrectionDeadline"))
            End If
        Catch ex As Exception
            MessageBox.Show("خطأ في تحميل التفاصيل: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

End Class
