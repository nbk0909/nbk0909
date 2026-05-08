Imports System.Data
Imports System.Data.SqlClient

''' <summary>
''' شاشة إدارة المستخدمين - متاحة للمدير فقط
''' </summary>
Public Class FrmUsers

    Private _currentId As Integer = 0

    Private Sub FrmUsers_Load(sender As Object, e As EventArgs) Handles MyBase.Load
        LoadGrid()
        ClearForm()
    End Sub

    Private Sub LoadGrid()
        Try
            Dim sql = "SELECT UserId AS [الرقم],
                              Username AS [اسم المستخدم],
                              FullName AS [الاسم الكامل],
                              Role AS [الصلاحية],
                              CASE WHEN IsActive = 1 THEN N'نشط' ELSE N'موقوف' END AS [الحالة],
                              LastLogin AS [آخر دخول],
                              CreatedAt AS [تاريخ الإنشاء]
                       FROM dbo.Users
                       ORDER BY UserId"
            grdUsers.DataSource = DatabaseHelper.ExecuteQuery(sql)
        Catch ex As Exception
            MessageBox.Show("خطأ في تحميل البيانات: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub ClearForm()
        _currentId = 0
        txtUsername.Clear() : txtPassword.Clear() : txtFullName.Clear()
        cmbRole.SelectedIndex = 1
        chkActive.Checked = True
        txtUsername.ReadOnly = False
        txtUsername.Focus()
    End Sub

    Private Sub btnNew_Click(sender As Object, e As EventArgs) Handles btnNew.Click
        ClearForm()
    End Sub

    Private Sub btnRefresh_Click(sender As Object, e As EventArgs) Handles btnRefresh.Click
        LoadGrid()
    End Sub

    Private Sub btnSave_Click(sender As Object, e As EventArgs) Handles btnSave.Click
        If String.IsNullOrWhiteSpace(txtUsername.Text) OrElse String.IsNullOrWhiteSpace(txtFullName.Text) Then
            MessageBox.Show("الرجاء إدخال اسم المستخدم والاسم الكامل.", "تنبيه",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If

        If _currentId = 0 AndAlso String.IsNullOrEmpty(txtPassword.Text) Then
            MessageBox.Show("الرجاء إدخال كلمة مرور للمستخدم الجديد.", "تنبيه",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If

        Try
            Dim params As New List(Of SqlParameter) From {
                New SqlParameter("@user", txtUsername.Text.Trim()),
                New SqlParameter("@name", txtFullName.Text.Trim()),
                New SqlParameter("@role", cmbRole.Text),
                New SqlParameter("@active", chkActive.Checked)
            }

            Dim sql As String
            If _currentId = 0 Then
                params.Add(New SqlParameter("@pwd", DatabaseHelper.HashPassword(txtPassword.Text)))
                sql = "INSERT INTO dbo.Users (Username, PasswordHash, FullName, Role, IsActive)
                       VALUES (@user, @pwd, @name, @role, @active)"
            Else
                params.Add(New SqlParameter("@id", _currentId))
                If String.IsNullOrEmpty(txtPassword.Text) Then
                    sql = "UPDATE dbo.Users SET
                              Username=@user, FullName=@name, Role=@role, IsActive=@active
                           WHERE UserId=@id"
                Else
                    params.Add(New SqlParameter("@pwd", DatabaseHelper.HashPassword(txtPassword.Text)))
                    sql = "UPDATE dbo.Users SET
                              Username=@user, PasswordHash=@pwd, FullName=@name, Role=@role, IsActive=@active
                           WHERE UserId=@id"
                End If
            End If

            DatabaseHelper.ExecuteNonQuery(sql, params.ToArray())
            MessageBox.Show("تم حفظ بيانات المستخدم بنجاح.", "نجاح",
                            MessageBoxButtons.OK, MessageBoxIcon.Information)
            LoadGrid()
            ClearForm()
        Catch ex As SqlException When ex.Number = 2627
            MessageBox.Show("اسم المستخدم مسجل مسبقاً. الرجاء استخدام اسم آخر.",
                            "تكرار", MessageBoxButtons.OK, MessageBoxIcon.Warning)
        Catch ex As Exception
            MessageBox.Show("خطأ في حفظ البيانات: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub btnDelete_Click(sender As Object, e As EventArgs) Handles btnDelete.Click
        If _currentId = 0 Then
            MessageBox.Show("الرجاء اختيار مستخدم من القائمة.", "تنبيه",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If

        If _currentId = SessionManager.UserId Then
            MessageBox.Show("لا يمكنك حذف حسابك الحالي.", "تنبيه",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If

        If MessageBox.Show("هل تريد بالتأكيد حذف هذا المستخدم؟", "تأكيد الحذف",
                           MessageBoxButtons.YesNo, MessageBoxIcon.Question) <> DialogResult.Yes Then
            Return
        End If

        Try
            DatabaseHelper.ExecuteNonQuery(
                "DELETE FROM dbo.Users WHERE UserId=@id",
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

    Private Sub grdUsers_CellClick(sender As Object, e As DataGridViewCellEventArgs) Handles grdUsers.CellClick
        If e.RowIndex < 0 Then Return
        _currentId = CInt(grdUsers.Rows(e.RowIndex).Cells("الرقم").Value)
        Try
            Dim dt = DatabaseHelper.ExecuteQuery(
                "SELECT * FROM dbo.Users WHERE UserId=@id",
                New SqlParameter("@id", _currentId))
            If dt.Rows.Count = 0 Then Return
            Dim r = dt.Rows(0)
            txtUsername.Text = r("Username").ToString()
            txtUsername.ReadOnly = True
            txtPassword.Clear()
            txtFullName.Text = r("FullName").ToString()
            cmbRole.Text = r("Role").ToString()
            chkActive.Checked = CBool(r("IsActive"))
        Catch ex As Exception
            MessageBox.Show("خطأ في تحميل التفاصيل: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

End Class
