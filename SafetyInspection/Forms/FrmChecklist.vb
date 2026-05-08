Imports System.Data
Imports System.Data.SqlClient

''' <summary>
''' شاشة إدارة بنود قائمة فحص السلامة
''' </summary>
Public Class FrmChecklist

    Private _currentId As Integer = 0

    Private Sub FrmChecklist_Load(sender As Object, e As EventArgs) Handles MyBase.Load
        LoadGrid()
        ClearForm()
    End Sub

    Private Sub LoadGrid()
        Try
            Dim sql = "SELECT ItemId AS [الرقم],
                              Category AS [الفئة],
                              ItemText AS [البند],
                              CASE WHEN IsCritical = 1 THEN N'حرج' ELSE N'عادي' END AS [التصنيف],
                              CASE WHEN IsActive = 1 THEN N'نشط' ELSE N'غير نشط' END AS [الحالة]
                       FROM dbo.ChecklistItems
                       ORDER BY Category, ItemId"
            grdItems.DataSource = DatabaseHelper.ExecuteQuery(sql)
        Catch ex As Exception
            MessageBox.Show("خطأ في تحميل البيانات: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub ClearForm()
        _currentId = 0
        cmbCategory.SelectedIndex = -1
        txtItem.Clear()
        chkCritical.Checked = False
        chkActive.Checked = True
    End Sub

    Private Sub btnNew_Click(sender As Object, e As EventArgs) Handles btnNew.Click
        ClearForm()
    End Sub

    Private Sub btnRefresh_Click(sender As Object, e As EventArgs) Handles btnRefresh.Click
        LoadGrid()
    End Sub

    Private Sub btnSave_Click(sender As Object, e As EventArgs) Handles btnSave.Click
        If String.IsNullOrEmpty(cmbCategory.Text) OrElse String.IsNullOrWhiteSpace(txtItem.Text) Then
            MessageBox.Show("الرجاء إدخال الفئة ونص البند.", "تنبيه",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If

        Try
            Dim params As New List(Of SqlParameter) From {
                New SqlParameter("@cat", cmbCategory.Text),
                New SqlParameter("@text", txtItem.Text.Trim()),
                New SqlParameter("@crit", chkCritical.Checked),
                New SqlParameter("@active", chkActive.Checked)
            }

            Dim sql As String
            If _currentId = 0 Then
                sql = "INSERT INTO dbo.ChecklistItems (Category, ItemText, IsCritical, IsActive)
                       VALUES (@cat, @text, @crit, @active)"
            Else
                sql = "UPDATE dbo.ChecklistItems SET
                          Category=@cat, ItemText=@text, IsCritical=@crit, IsActive=@active
                       WHERE ItemId=@id"
                params.Add(New SqlParameter("@id", _currentId))
            End If

            DatabaseHelper.ExecuteNonQuery(sql, params.ToArray())
            MessageBox.Show("تم حفظ البند بنجاح.", "نجاح",
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
            MessageBox.Show("الرجاء اختيار بند من القائمة.", "تنبيه",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If
        If MessageBox.Show("هل تريد بالتأكيد حذف هذا البند؟", "تأكيد الحذف",
                           MessageBoxButtons.YesNo, MessageBoxIcon.Question) <> DialogResult.Yes Then
            Return
        End If
        Try
            DatabaseHelper.ExecuteNonQuery(
                "DELETE FROM dbo.ChecklistItems WHERE ItemId=@id",
                New SqlParameter("@id", _currentId))
            MessageBox.Show("تم الحذف بنجاح.", "نجاح",
                            MessageBoxButtons.OK, MessageBoxIcon.Information)
            LoadGrid()
            ClearForm()
        Catch ex As SqlException When ex.Number = 547
            MessageBox.Show("لا يمكن حذف هذا البند لاستخدامه في تفتيشات سابقة. يمكن تعطيله بدلاً من ذلك.",
                            "تعذر الحذف", MessageBoxButtons.OK, MessageBoxIcon.Warning)
        Catch ex As Exception
            MessageBox.Show("خطأ في الحذف: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub grdItems_CellClick(sender As Object, e As DataGridViewCellEventArgs) Handles grdItems.CellClick
        If e.RowIndex < 0 Then Return
        _currentId = CInt(grdItems.Rows(e.RowIndex).Cells("الرقم").Value)
        Try
            Dim dt = DatabaseHelper.ExecuteQuery(
                "SELECT * FROM dbo.ChecklistItems WHERE ItemId=@id",
                New SqlParameter("@id", _currentId))
            If dt.Rows.Count = 0 Then Return
            Dim r = dt.Rows(0)
            cmbCategory.Text = r("Category").ToString()
            txtItem.Text = r("ItemText").ToString()
            chkCritical.Checked = CBool(r("IsCritical"))
            chkActive.Checked = CBool(r("IsActive"))
        Catch ex As Exception
            MessageBox.Show("خطأ في تحميل التفاصيل: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

End Class
