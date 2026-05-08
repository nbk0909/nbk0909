Imports System.Data
Imports System.Data.SqlClient

''' <summary>
''' شاشة إدارة المنشآت - إضافة وتعديل وحذف المنشآت
''' </summary>
Public Class FrmEstablishments

    Private _currentId As Integer = 0

    Private Sub FrmEstablishments_Load(sender As Object, e As EventArgs) Handles MyBase.Load
        LoadGrid()
        ClearForm()
    End Sub

    Private Sub LoadGrid(Optional searchTerm As String = "")
        Try
            Dim sql As String =
                "SELECT EstablishmentId AS [الرقم], EstablishmentName AS [اسم المنشأة],
                        RegistrationNo AS [رقم السجل], Sector AS [القطاع],
                        City AS [المدينة], Phone AS [الهاتف], OwnerName AS [المالك],
                        EmployeesCount AS [عدد العاملين], RiskLevel AS [مستوى المخاطر]
                 FROM dbo.Establishments
                 WHERE (@s = '' OR EstablishmentName LIKE '%' + @s + '%'
                                OR RegistrationNo LIKE '%' + @s + '%'
                                OR City LIKE '%' + @s + '%')
                 ORDER BY EstablishmentId DESC"
            Dim dt = DatabaseHelper.ExecuteQuery(sql, New SqlParameter("@s", searchTerm))
            grdEstablishments.DataSource = dt
        Catch ex As Exception
            MessageBox.Show("خطأ في تحميل البيانات: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub ClearForm()
        _currentId = 0
        txtName.Clear()
        txtRegNo.Clear()
        cmbSector.SelectedIndex = -1
        txtActivity.Clear()
        txtAddress.Clear()
        txtCity.Clear()
        txtPhone.Clear()
        txtEmail.Clear()
        txtOwner.Clear()
        numEmployees.Value = 0
        cmbRisk.SelectedIndex = 1
        txtName.Focus()
    End Sub

    Private Sub btnNew_Click(sender As Object, e As EventArgs) Handles btnNew.Click
        ClearForm()
    End Sub

    Private Sub btnRefresh_Click(sender As Object, e As EventArgs) Handles btnRefresh.Click
        txtSearch.Clear()
        LoadGrid()
    End Sub

    Private Sub txtSearch_TextChanged(sender As Object, e As EventArgs) Handles txtSearch.TextChanged
        LoadGrid(txtSearch.Text.Trim())
    End Sub

    Private Sub btnSave_Click(sender As Object, e As EventArgs) Handles btnSave.Click
        If String.IsNullOrWhiteSpace(txtName.Text) Then
            MessageBox.Show("الرجاء إدخال اسم المنشأة.", "تنبيه",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning)
            txtName.Focus()
            Return
        End If

        Try
            Dim params As New List(Of SqlParameter) From {
                New SqlParameter("@name", txtName.Text.Trim()),
                New SqlParameter("@reg", If(String.IsNullOrWhiteSpace(txtRegNo.Text), CObj(DBNull.Value), txtRegNo.Text.Trim())),
                New SqlParameter("@sector", If(cmbSector.SelectedItem Is Nothing, CObj(DBNull.Value), cmbSector.SelectedItem.ToString())),
                New SqlParameter("@activity", If(String.IsNullOrWhiteSpace(txtActivity.Text), CObj(DBNull.Value), txtActivity.Text.Trim())),
                New SqlParameter("@address", If(String.IsNullOrWhiteSpace(txtAddress.Text), CObj(DBNull.Value), txtAddress.Text.Trim())),
                New SqlParameter("@city", If(String.IsNullOrWhiteSpace(txtCity.Text), CObj(DBNull.Value), txtCity.Text.Trim())),
                New SqlParameter("@phone", If(String.IsNullOrWhiteSpace(txtPhone.Text), CObj(DBNull.Value), txtPhone.Text.Trim())),
                New SqlParameter("@email", If(String.IsNullOrWhiteSpace(txtEmail.Text), CObj(DBNull.Value), txtEmail.Text.Trim())),
                New SqlParameter("@owner", If(String.IsNullOrWhiteSpace(txtOwner.Text), CObj(DBNull.Value), txtOwner.Text.Trim())),
                New SqlParameter("@emp", CInt(numEmployees.Value)),
                New SqlParameter("@risk", If(cmbRisk.SelectedItem Is Nothing, "متوسط", cmbRisk.SelectedItem.ToString()))
            }

            Dim sql As String
            If _currentId = 0 Then
                sql = "INSERT INTO dbo.Establishments
                       (EstablishmentName, RegistrationNo, Sector, ActivityType, Address, City,
                        Phone, Email, OwnerName, EmployeesCount, RiskLevel)
                       VALUES (@name, @reg, @sector, @activity, @address, @city,
                               @phone, @email, @owner, @emp, @risk)"
            Else
                sql = "UPDATE dbo.Establishments SET
                          EstablishmentName=@name, RegistrationNo=@reg, Sector=@sector,
                          ActivityType=@activity, Address=@address, City=@city,
                          Phone=@phone, Email=@email, OwnerName=@owner,
                          EmployeesCount=@emp, RiskLevel=@risk
                       WHERE EstablishmentId=@id"
                params.Add(New SqlParameter("@id", _currentId))
            End If

            DatabaseHelper.ExecuteNonQuery(sql, params.ToArray())
            MessageBox.Show("تم حفظ البيانات بنجاح.", "نجاح",
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
            MessageBox.Show("الرجاء اختيار منشأة من القائمة.", "تنبيه",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If

        If MessageBox.Show("هل تريد بالتأكيد حذف هذه المنشأة؟", "تأكيد الحذف",
                           MessageBoxButtons.YesNo, MessageBoxIcon.Question) <> DialogResult.Yes Then
            Return
        End If

        Try
            DatabaseHelper.ExecuteNonQuery(
                "DELETE FROM dbo.Establishments WHERE EstablishmentId=@id",
                New SqlParameter("@id", _currentId))
            MessageBox.Show("تم الحذف بنجاح.", "نجاح",
                            MessageBoxButtons.OK, MessageBoxIcon.Information)
            LoadGrid()
            ClearForm()
        Catch ex As SqlException When ex.Number = 547
            MessageBox.Show("لا يمكن حذف هذه المنشأة لارتباطها بسجلات تفتيش.", "تعذر الحذف",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning)
        Catch ex As Exception
            MessageBox.Show("خطأ في الحذف: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub grdEstablishments_CellClick(sender As Object, e As DataGridViewCellEventArgs) Handles grdEstablishments.CellClick
        If e.RowIndex < 0 Then Return
        Dim row = grdEstablishments.Rows(e.RowIndex)
        _currentId = CInt(row.Cells("الرقم").Value)
        Try
            Dim dt = DatabaseHelper.ExecuteQuery(
                "SELECT * FROM dbo.Establishments WHERE EstablishmentId=@id",
                New SqlParameter("@id", _currentId))
            If dt.Rows.Count = 0 Then Return
            Dim r = dt.Rows(0)
            txtName.Text = r("EstablishmentName").ToString()
            txtRegNo.Text = If(IsDBNull(r("RegistrationNo")), "", r("RegistrationNo").ToString())
            cmbSector.Text = If(IsDBNull(r("Sector")), "", r("Sector").ToString())
            txtActivity.Text = If(IsDBNull(r("ActivityType")), "", r("ActivityType").ToString())
            txtAddress.Text = If(IsDBNull(r("Address")), "", r("Address").ToString())
            txtCity.Text = If(IsDBNull(r("City")), "", r("City").ToString())
            txtPhone.Text = If(IsDBNull(r("Phone")), "", r("Phone").ToString())
            txtEmail.Text = If(IsDBNull(r("Email")), "", r("Email").ToString())
            txtOwner.Text = If(IsDBNull(r("OwnerName")), "", r("OwnerName").ToString())
            numEmployees.Value = CInt(r("EmployeesCount"))
            cmbRisk.Text = r("RiskLevel").ToString()
        Catch ex As Exception
            MessageBox.Show("خطأ في تحميل التفاصيل: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

End Class
