Imports System.Data
Imports System.Data.SqlClient

''' <summary>
''' شاشة إدارة المفتشين
''' </summary>
Public Class FrmInspectors

    Private _currentId As Integer = 0

    Private Sub FrmInspectors_Load(sender As Object, e As EventArgs) Handles MyBase.Load
        LoadGrid()
        ClearForm()
    End Sub

    Private Sub LoadGrid()
        Try
            Dim sql = "SELECT InspectorId AS [الرقم], EmployeeNo AS [الرقم الوظيفي],
                              FullName AS [الاسم], Specialization AS [التخصص],
                              Phone AS [الهاتف], Email AS [البريد],
                              HireDate AS [تاريخ التعيين],
                              CASE WHEN IsActive = 1 THEN N'نشط' ELSE N'غير نشط' END AS [الحالة]
                       FROM dbo.Inspectors
                       ORDER BY InspectorId DESC"
            grdInspectors.DataSource = DatabaseHelper.ExecuteQuery(sql)
        Catch ex As Exception
            MessageBox.Show("خطأ في تحميل البيانات: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub ClearForm()
        _currentId = 0
        txtEmpNo.Clear() : txtName.Clear() : txtNationalId.Clear()
        cmbSpec.SelectedIndex = -1
        txtPhone.Clear() : txtEmail.Clear()
        dtpHire.Value = DateTime.Today
        chkActive.Checked = True
        txtEmpNo.Focus()
    End Sub

    Private Sub btnNew_Click(sender As Object, e As EventArgs) Handles btnNew.Click
        ClearForm()
    End Sub

    Private Sub btnRefresh_Click(sender As Object, e As EventArgs) Handles btnRefresh.Click
        LoadGrid()
    End Sub

    Private Sub btnSave_Click(sender As Object, e As EventArgs) Handles btnSave.Click
        If String.IsNullOrWhiteSpace(txtEmpNo.Text) OrElse String.IsNullOrWhiteSpace(txtName.Text) Then
            MessageBox.Show("الرجاء إدخال الرقم الوظيفي والاسم.", "تنبيه",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If

        Try
            Dim params As New List(Of SqlParameter) From {
                New SqlParameter("@emp", txtEmpNo.Text.Trim()),
                New SqlParameter("@name", txtName.Text.Trim()),
                New SqlParameter("@nat", If(String.IsNullOrWhiteSpace(txtNationalId.Text), CObj(DBNull.Value), txtNationalId.Text.Trim())),
                New SqlParameter("@spec", If(cmbSpec.SelectedItem Is Nothing, CObj(DBNull.Value), cmbSpec.SelectedItem.ToString())),
                New SqlParameter("@phone", If(String.IsNullOrWhiteSpace(txtPhone.Text), CObj(DBNull.Value), txtPhone.Text.Trim())),
                New SqlParameter("@email", If(String.IsNullOrWhiteSpace(txtEmail.Text), CObj(DBNull.Value), txtEmail.Text.Trim())),
                New SqlParameter("@hire", dtpHire.Value.Date),
                New SqlParameter("@active", chkActive.Checked)
            }

            Dim sql As String
            If _currentId = 0 Then
                sql = "INSERT INTO dbo.Inspectors
                       (EmployeeNo, FullName, NationalId, Specialization, Phone, Email, HireDate, IsActive)
                       VALUES (@emp, @name, @nat, @spec, @phone, @email, @hire, @active)"
            Else
                sql = "UPDATE dbo.Inspectors SET
                          EmployeeNo=@emp, FullName=@name, NationalId=@nat,
                          Specialization=@spec, Phone=@phone, Email=@email,
                          HireDate=@hire, IsActive=@active
                       WHERE InspectorId=@id"
                params.Add(New SqlParameter("@id", _currentId))
            End If

            DatabaseHelper.ExecuteNonQuery(sql, params.ToArray())
            MessageBox.Show("تم حفظ البيانات بنجاح.", "نجاح",
                            MessageBoxButtons.OK, MessageBoxIcon.Information)
            LoadGrid()
            ClearForm()
        Catch ex As SqlException When ex.Number = 2627
            MessageBox.Show("الرقم الوظيفي مسجل مسبقاً. الرجاء استخدام رقم آخر.",
                            "تكرار", MessageBoxButtons.OK, MessageBoxIcon.Warning)
        Catch ex As Exception
            MessageBox.Show("خطأ في حفظ البيانات: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub btnDelete_Click(sender As Object, e As EventArgs) Handles btnDelete.Click
        If _currentId = 0 Then
            MessageBox.Show("الرجاء اختيار مفتش من القائمة.", "تنبيه",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If
        If MessageBox.Show("هل تريد بالتأكيد حذف هذا المفتش؟", "تأكيد الحذف",
                           MessageBoxButtons.YesNo, MessageBoxIcon.Question) <> DialogResult.Yes Then
            Return
        End If
        Try
            DatabaseHelper.ExecuteNonQuery(
                "DELETE FROM dbo.Inspectors WHERE InspectorId=@id",
                New SqlParameter("@id", _currentId))
            MessageBox.Show("تم الحذف بنجاح.", "نجاح",
                            MessageBoxButtons.OK, MessageBoxIcon.Information)
            LoadGrid()
            ClearForm()
        Catch ex As SqlException When ex.Number = 547
            MessageBox.Show("لا يمكن حذف هذا المفتش لارتباطه بسجلات تفتيش.", "تعذر الحذف",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning)
        Catch ex As Exception
            MessageBox.Show("خطأ في الحذف: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub grdInspectors_CellClick(sender As Object, e As DataGridViewCellEventArgs) Handles grdInspectors.CellClick
        If e.RowIndex < 0 Then Return
        _currentId = CInt(grdInspectors.Rows(e.RowIndex).Cells("الرقم").Value)
        Try
            Dim dt = DatabaseHelper.ExecuteQuery(
                "SELECT * FROM dbo.Inspectors WHERE InspectorId=@id",
                New SqlParameter("@id", _currentId))
            If dt.Rows.Count = 0 Then Return
            Dim r = dt.Rows(0)
            txtEmpNo.Text = r("EmployeeNo").ToString()
            txtName.Text = r("FullName").ToString()
            txtNationalId.Text = If(IsDBNull(r("NationalId")), "", r("NationalId").ToString())
            cmbSpec.Text = If(IsDBNull(r("Specialization")), "", r("Specialization").ToString())
            txtPhone.Text = If(IsDBNull(r("Phone")), "", r("Phone").ToString())
            txtEmail.Text = If(IsDBNull(r("Email")), "", r("Email").ToString())
            If Not IsDBNull(r("HireDate")) Then dtpHire.Value = CDate(r("HireDate"))
            chkActive.Checked = CBool(r("IsActive"))
        Catch ex As Exception
            MessageBox.Show("خطأ في تحميل البيانات: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

End Class
