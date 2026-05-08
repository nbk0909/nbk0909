Imports System.Data
Imports System.Data.SqlClient

''' <summary>
''' شاشة إدارة زيارات التفتيش
''' </summary>
Public Class FrmInspections

    Private _currentId As Integer = 0

    Private Sub FrmInspections_Load(sender As Object, e As EventArgs) Handles MyBase.Load
        LoadEstablishments()
        LoadInspectors()
        LoadGrid()
        ClearForm()
    End Sub

    Private Sub LoadEstablishments()
        Try
            Dim dt = DatabaseHelper.ExecuteQuery(
                "SELECT EstablishmentId, EstablishmentName FROM dbo.Establishments ORDER BY EstablishmentName")
            cmbEst.DataSource = dt
            cmbEst.DisplayMember = "EstablishmentName"
            cmbEst.ValueMember = "EstablishmentId"
            cmbEst.SelectedIndex = -1
        Catch ex As Exception
            MessageBox.Show("خطأ في تحميل المنشآت: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub LoadInspectors()
        Try
            Dim dt = DatabaseHelper.ExecuteQuery(
                "SELECT InspectorId, FullName FROM dbo.Inspectors WHERE IsActive=1 ORDER BY FullName")
            cmbInsp.DataSource = dt
            cmbInsp.DisplayMember = "FullName"
            cmbInsp.ValueMember = "InspectorId"
            cmbInsp.SelectedIndex = -1
        Catch ex As Exception
            MessageBox.Show("خطأ في تحميل المفتشين: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub LoadGrid()
        Try
            Dim sql = "SELECT i.InspectionId AS [الرقم],
                              e.EstablishmentName AS [المنشأة],
                              ins.FullName AS [المفتش],
                              i.InspectionDate AS [التاريخ],
                              i.InspectionType AS [النوع],
                              i.Status AS [الحالة],
                              i.OverallRating AS [التقييم],
                              (SELECT COUNT(*) FROM dbo.Violations v WHERE v.InspectionId = i.InspectionId) AS [عدد المخالفات]
                       FROM dbo.Inspections i
                       INNER JOIN dbo.Establishments e ON e.EstablishmentId = i.EstablishmentId
                       INNER JOIN dbo.Inspectors    ins ON ins.InspectorId    = i.InspectorId
                       ORDER BY i.InspectionDate DESC, i.InspectionId DESC"
            grdInspections.DataSource = DatabaseHelper.ExecuteQuery(sql)
        Catch ex As Exception
            MessageBox.Show("خطأ في تحميل البيانات: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub ClearForm()
        _currentId = 0
        cmbEst.SelectedIndex = -1
        cmbInsp.SelectedIndex = -1
        dtpDate.Value = DateTime.Today
        cmbType.SelectedIndex = 0
        cmbStatus.SelectedIndex = 0
        cmbRating.SelectedIndex = -1
        txtNotes.Clear()
    End Sub

    Private Sub btnNew_Click(sender As Object, e As EventArgs) Handles btnNew.Click
        ClearForm()
    End Sub

    Private Sub btnRefresh_Click(sender As Object, e As EventArgs) Handles btnRefresh.Click
        LoadEstablishments()
        LoadInspectors()
        LoadGrid()
    End Sub

    Private Sub btnSave_Click(sender As Object, e As EventArgs) Handles btnSave.Click
        If cmbEst.SelectedValue Is Nothing OrElse cmbInsp.SelectedValue Is Nothing Then
            MessageBox.Show("الرجاء اختيار المنشأة والمفتش.", "تنبيه",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If

        Try
            Dim params As New List(Of SqlParameter) From {
                New SqlParameter("@est", CInt(cmbEst.SelectedValue)),
                New SqlParameter("@insp", CInt(cmbInsp.SelectedValue)),
                New SqlParameter("@date", dtpDate.Value.Date),
                New SqlParameter("@type", cmbType.Text),
                New SqlParameter("@status", cmbStatus.Text),
                New SqlParameter("@rating", If(String.IsNullOrEmpty(cmbRating.Text), CObj(DBNull.Value), cmbRating.Text)),
                New SqlParameter("@notes", If(String.IsNullOrEmpty(txtNotes.Text), CObj(DBNull.Value), txtNotes.Text))
            }

            Dim sql As String
            If _currentId = 0 Then
                sql = "INSERT INTO dbo.Inspections
                       (EstablishmentId, InspectorId, InspectionDate, InspectionType, Status, OverallRating, Notes)
                       VALUES (@est, @insp, @date, @type, @status, @rating, @notes)"
            Else
                sql = "UPDATE dbo.Inspections SET
                          EstablishmentId=@est, InspectorId=@insp, InspectionDate=@date,
                          InspectionType=@type, Status=@status, OverallRating=@rating, Notes=@notes
                       WHERE InspectionId=@id"
                params.Add(New SqlParameter("@id", _currentId))
            End If

            DatabaseHelper.ExecuteNonQuery(sql, params.ToArray())
            MessageBox.Show("تم حفظ بيانات التفتيش بنجاح.", "نجاح",
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
            MessageBox.Show("الرجاء اختيار تفتيش من القائمة.", "تنبيه",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If
        If MessageBox.Show("سيتم حذف التفتيش وجميع المخالفات المرتبطة به. هل تريد المتابعة؟",
                           "تأكيد الحذف", MessageBoxButtons.YesNo, MessageBoxIcon.Question) <> DialogResult.Yes Then
            Return
        End If
        Try
            DatabaseHelper.ExecuteNonQuery(
                "DELETE FROM dbo.Inspections WHERE InspectionId=@id",
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

    Private Sub btnViolations_Click(sender As Object, e As EventArgs) Handles btnViolations.Click
        If _currentId = 0 Then
            MessageBox.Show("الرجاء اختيار تفتيش أولاً لإدارة مخالفاته.", "تنبيه",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If
        Dim frm As New FrmViolations(_currentId)
        frm.MdiParent = Me.MdiParent
        frm.WindowState = FormWindowState.Maximized
        frm.Show()
    End Sub

    Private Sub grdInspections_CellClick(sender As Object, e As DataGridViewCellEventArgs) Handles grdInspections.CellClick
        If e.RowIndex < 0 Then Return
        _currentId = CInt(grdInspections.Rows(e.RowIndex).Cells("الرقم").Value)
        Try
            Dim dt = DatabaseHelper.ExecuteQuery(
                "SELECT * FROM dbo.Inspections WHERE InspectionId=@id",
                New SqlParameter("@id", _currentId))
            If dt.Rows.Count = 0 Then Return
            Dim r = dt.Rows(0)
            cmbEst.SelectedValue = CInt(r("EstablishmentId"))
            cmbInsp.SelectedValue = CInt(r("InspectorId"))
            dtpDate.Value = CDate(r("InspectionDate"))
            cmbType.Text = r("InspectionType").ToString()
            cmbStatus.Text = r("Status").ToString()
            cmbRating.Text = If(IsDBNull(r("OverallRating")), "", r("OverallRating").ToString())
            txtNotes.Text = If(IsDBNull(r("Notes")), "", r("Notes").ToString())
        Catch ex As Exception
            MessageBox.Show("خطأ في تحميل التفاصيل: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

End Class
