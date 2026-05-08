Imports System.Data
Imports System.Data.SqlClient

''' <summary>
''' شاشة تسجيل الدخول للنظام
''' </summary>
Public Class FrmLogin

    Private Sub FrmLogin_Load(sender As Object, e As EventArgs) Handles MyBase.Load
        txtUsername.Focus()
    End Sub

    Private Sub btnLogin_Click(sender As Object, e As EventArgs) Handles btnLogin.Click
        DoLogin()
    End Sub

    Private Sub btnExit_Click(sender As Object, e As EventArgs) Handles btnExit.Click
        Me.DialogResult = DialogResult.Cancel
        Me.Close()
    End Sub

    Private Sub DoLogin()
        Dim username = txtUsername.Text.Trim()
        Dim password = txtPassword.Text

        If String.IsNullOrEmpty(username) OrElse String.IsNullOrEmpty(password) Then
            MessageBox.Show("الرجاء إدخال اسم المستخدم وكلمة المرور.",
                            "تنبيه", MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If

        If Not DatabaseHelper.TestConnection() Then
            MessageBox.Show("تعذر الاتصال بقاعدة البيانات. يرجى التأكد من تشغيل خادم SQL Server وتنفيذ سكربت إنشاء قاعدة البيانات.",
                            "خطأ في الاتصال", MessageBoxButtons.OK, MessageBoxIcon.Error)
            Return
        End If

        Try
            Dim hash = DatabaseHelper.HashPassword(password)
            Dim sql = "SELECT UserId, Username, FullName, Role, IsActive
                       FROM dbo.Users
                       WHERE Username = @u AND PasswordHash = @p"

            Dim dt = DatabaseHelper.ExecuteQuery(sql,
                New SqlParameter("@u", username),
                New SqlParameter("@p", hash))

            If dt.Rows.Count = 0 Then
                MessageBox.Show("اسم المستخدم أو كلمة المرور غير صحيحة.",
                                "خطأ في تسجيل الدخول", MessageBoxButtons.OK, MessageBoxIcon.Error)
                txtPassword.Clear()
                txtPassword.Focus()
                Return
            End If

            Dim row = dt.Rows(0)
            If Not CBool(row("IsActive")) Then
                MessageBox.Show("هذا الحساب موقوف. يرجى مراجعة مدير النظام.",
                                "حساب موقوف", MessageBoxButtons.OK, MessageBoxIcon.Warning)
                Return
            End If

            ' حفظ بيانات الجلسة
            SessionManager.UserId = CInt(row("UserId"))
            SessionManager.Username = row("Username").ToString()
            SessionManager.FullName = row("FullName").ToString()
            SessionManager.Role = row("Role").ToString()

            ' تحديث وقت آخر دخول
            DatabaseHelper.ExecuteNonQuery(
                "UPDATE dbo.Users SET LastLogin = GETDATE() WHERE UserId = @id",
                New SqlParameter("@id", SessionManager.UserId))

            Me.DialogResult = DialogResult.OK
            Me.Close()

        Catch ex As Exception
            MessageBox.Show("حدث خطأ غير متوقع: " & ex.Message,
                            "خطأ", MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

End Class
