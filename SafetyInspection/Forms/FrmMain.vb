''' <summary>
''' الشاشة الرئيسية - حاوية MDI للنوافذ الفرعية
''' </summary>
Public Class FrmMain

    Private Sub FrmMain_Load(sender As Object, e As EventArgs) Handles MyBase.Load
        lblUser.Text = "المستخدم: " & SessionManager.FullName
        lblRole.Text = "الصلاحية: " & SessionManager.Role
        UpdateClock()

        ' إخفاء قائمة إدارة النظام لغير المدير
        mnuAdmin.Visible = SessionManager.IsAdmin
    End Sub

    Private Sub tmrClock_Tick(sender As Object, e As EventArgs) Handles tmrClock.Tick
        UpdateClock()
    End Sub

    Private Sub UpdateClock()
        lblDate.Text = "التاريخ: " & DateTime.Now.ToString("yyyy/MM/dd  HH:mm:ss")
    End Sub

    ''' <summary>عرض نموذج فرعي داخل الـ MDI - يمنع تكرار الفتح</summary>
    Private Sub OpenChild(Of T As {Form, New})()
        For Each frm As Form In Me.MdiChildren
            If TypeOf frm Is T Then
                frm.Activate()
                Return
            End If
        Next
        Dim newFrm As New T()
        newFrm.MdiParent = Me
        newFrm.WindowState = FormWindowState.Maximized
        newFrm.Show()
    End Sub

    Private Sub mnuLogout_Click(sender As Object, e As EventArgs) Handles mnuLogout.Click
        If MessageBox.Show("هل تريد تسجيل الخروج من النظام؟", "تأكيد",
                           MessageBoxButtons.YesNo, MessageBoxIcon.Question) = DialogResult.Yes Then
            SessionManager.Logout()
            Application.Restart()
        End If
    End Sub

    Private Sub mnuExit_Click(sender As Object, e As EventArgs) Handles mnuExit.Click
        If MessageBox.Show("هل تريد الخروج من البرنامج؟", "تأكيد",
                           MessageBoxButtons.YesNo, MessageBoxIcon.Question) = DialogResult.Yes Then
            Application.Exit()
        End If
    End Sub

    Private Sub mnuEstablishments_Click(sender As Object, e As EventArgs) Handles mnuEstablishments.Click
        OpenChild(Of FrmEstablishments)()
    End Sub

    Private Sub mnuInspectors_Click(sender As Object, e As EventArgs) Handles mnuInspectors.Click
        OpenChild(Of FrmInspectors)()
    End Sub

    Private Sub mnuChecklist_Click(sender As Object, e As EventArgs) Handles mnuChecklist.Click
        OpenChild(Of FrmChecklist)()
    End Sub

    Private Sub mnuInspections_Click(sender As Object, e As EventArgs) Handles mnuInspections.Click
        OpenChild(Of FrmInspections)()
    End Sub

    Private Sub mnuViolations_Click(sender As Object, e As EventArgs) Handles mnuViolations.Click
        OpenChild(Of FrmViolations)()
    End Sub

    Private Sub mnuRptInspections_Click(sender As Object, e As EventArgs) Handles mnuRptInspections.Click
        OpenChild(Of FrmReports)()
    End Sub

    Private Sub mnuRptViolations_Click(sender As Object, e As EventArgs) Handles mnuRptViolations.Click
        OpenChild(Of FrmReports)()
    End Sub

    Private Sub mnuRptStats_Click(sender As Object, e As EventArgs) Handles mnuRptStats.Click
        OpenChild(Of FrmReports)()
    End Sub

    Private Sub mnuUsers_Click(sender As Object, e As EventArgs) Handles mnuUsers.Click
        If Not SessionManager.IsAdmin Then
            MessageBox.Show("لا تملك صلاحية الوصول إلى هذه الشاشة.", "تنبيه",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If
        OpenChild(Of FrmUsers)()
    End Sub

    Private Sub mnuAbout_Click(sender As Object, e As EventArgs) Handles mnuAbout.Click
        Dim msg As String =
            "برنامج تفتيش السلامة المهنية" & vbCrLf &
            "الإصدار: 1.0.0" & vbCrLf &
            "نظام متكامل لإدارة عمليات تفتيش السلامة والصحة المهنية" & vbCrLf &
            "في المنشآت الصناعية والتجارية والخدمية." & vbCrLf & vbCrLf &
            "© 2026 - جميع الحقوق محفوظة"
        MessageBox.Show(msg, "عن البرنامج", MessageBoxButtons.OK, MessageBoxIcon.Information)
    End Sub

End Class
