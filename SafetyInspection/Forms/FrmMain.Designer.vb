<Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()>
Partial Class FrmMain
    Inherits System.Windows.Forms.Form

    Private components As System.ComponentModel.IContainer

    <System.Diagnostics.DebuggerNonUserCode()>
    Protected Overrides Sub Dispose(ByVal disposing As Boolean)
        Try
            If disposing AndAlso components IsNot Nothing Then
                components.Dispose()
            End If
        Finally
            MyBase.Dispose(disposing)
        End Try
    End Sub

    Friend WithEvents menuStrip1 As MenuStrip
    Friend WithEvents mnuFile As ToolStripMenuItem
    Friend WithEvents mnuLogout As ToolStripMenuItem
    Friend WithEvents mnuExit As ToolStripMenuItem
    Friend WithEvents mnuData As ToolStripMenuItem
    Friend WithEvents mnuEstablishments As ToolStripMenuItem
    Friend WithEvents mnuInspectors As ToolStripMenuItem
    Friend WithEvents mnuChecklist As ToolStripMenuItem
    Friend WithEvents mnuOps As ToolStripMenuItem
    Friend WithEvents mnuInspections As ToolStripMenuItem
    Friend WithEvents mnuViolations As ToolStripMenuItem
    Friend WithEvents mnuReports As ToolStripMenuItem
    Friend WithEvents mnuRptInspections As ToolStripMenuItem
    Friend WithEvents mnuRptViolations As ToolStripMenuItem
    Friend WithEvents mnuRptStats As ToolStripMenuItem
    Friend WithEvents mnuAdmin As ToolStripMenuItem
    Friend WithEvents mnuUsers As ToolStripMenuItem
    Friend WithEvents mnuHelp As ToolStripMenuItem
    Friend WithEvents mnuAbout As ToolStripMenuItem
    Friend WithEvents statusStrip1 As StatusStrip
    Friend WithEvents lblUser As ToolStripStatusLabel
    Friend WithEvents lblRole As ToolStripStatusLabel
    Friend WithEvents lblDate As ToolStripStatusLabel
    Friend WithEvents lblSpring As ToolStripStatusLabel
    Friend WithEvents pnlBackground As Panel
    Friend WithEvents lblWelcome As Label
    Friend WithEvents tmrClock As Timer

    <System.Diagnostics.DebuggerStepThrough()>
    Private Sub InitializeComponent()
        Me.components = New System.ComponentModel.Container()
        Me.menuStrip1 = New MenuStrip()
        Me.mnuFile = New ToolStripMenuItem()
        Me.mnuLogout = New ToolStripMenuItem()
        Me.mnuExit = New ToolStripMenuItem()
        Me.mnuData = New ToolStripMenuItem()
        Me.mnuEstablishments = New ToolStripMenuItem()
        Me.mnuInspectors = New ToolStripMenuItem()
        Me.mnuChecklist = New ToolStripMenuItem()
        Me.mnuOps = New ToolStripMenuItem()
        Me.mnuInspections = New ToolStripMenuItem()
        Me.mnuViolations = New ToolStripMenuItem()
        Me.mnuReports = New ToolStripMenuItem()
        Me.mnuRptInspections = New ToolStripMenuItem()
        Me.mnuRptViolations = New ToolStripMenuItem()
        Me.mnuRptStats = New ToolStripMenuItem()
        Me.mnuAdmin = New ToolStripMenuItem()
        Me.mnuUsers = New ToolStripMenuItem()
        Me.mnuHelp = New ToolStripMenuItem()
        Me.mnuAbout = New ToolStripMenuItem()
        Me.statusStrip1 = New StatusStrip()
        Me.lblUser = New ToolStripStatusLabel()
        Me.lblRole = New ToolStripStatusLabel()
        Me.lblSpring = New ToolStripStatusLabel()
        Me.lblDate = New ToolStripStatusLabel()
        Me.pnlBackground = New Panel()
        Me.lblWelcome = New Label()
        Me.tmrClock = New Timer(Me.components)

        Me.menuStrip1.SuspendLayout()
        Me.statusStrip1.SuspendLayout()
        Me.pnlBackground.SuspendLayout()
        Me.SuspendLayout()
        '
        ' menuStrip1
        '
        Me.menuStrip1.BackColor = Color.FromArgb(31, 78, 120)
        Me.menuStrip1.Font = New Font("Tahoma", 11.0!)
        Me.menuStrip1.ForeColor = Color.White
        Me.menuStrip1.Items.AddRange(New ToolStripItem() {
            Me.mnuFile, Me.mnuData, Me.mnuOps, Me.mnuReports, Me.mnuAdmin, Me.mnuHelp})
        Me.menuStrip1.Location = New Point(0, 0)
        Me.menuStrip1.Padding = New Padding(6)
        Me.menuStrip1.RightToLeft = RightToLeft.Yes
        Me.menuStrip1.Size = New Size(1000, 35)
        '
        ' mnuFile
        '
        Me.mnuFile.DropDownItems.AddRange(New ToolStripItem() {Me.mnuLogout, Me.mnuExit})
        Me.mnuFile.Text = "ملف"
        Me.mnuFile.ForeColor = Color.White
        '
        ' mnuLogout
        '
        Me.mnuLogout.Text = "تسجيل الخروج"
        '
        ' mnuExit
        '
        Me.mnuExit.Text = "خروج من البرنامج"
        '
        ' mnuData
        '
        Me.mnuData.DropDownItems.AddRange(New ToolStripItem() {
            Me.mnuEstablishments, Me.mnuInspectors, Me.mnuChecklist})
        Me.mnuData.Text = "البيانات الأساسية"
        Me.mnuData.ForeColor = Color.White
        '
        ' mnuEstablishments
        '
        Me.mnuEstablishments.Text = "المنشآت"
        '
        ' mnuInspectors
        '
        Me.mnuInspectors.Text = "المفتشون"
        '
        ' mnuChecklist
        '
        Me.mnuChecklist.Text = "بنود قائمة الفحص"
        '
        ' mnuOps
        '
        Me.mnuOps.DropDownItems.AddRange(New ToolStripItem() {Me.mnuInspections, Me.mnuViolations})
        Me.mnuOps.Text = "العمليات"
        Me.mnuOps.ForeColor = Color.White
        '
        ' mnuInspections
        '
        Me.mnuInspections.Text = "زيارات التفتيش"
        '
        ' mnuViolations
        '
        Me.mnuViolations.Text = "المخالفات"
        '
        ' mnuReports
        '
        Me.mnuReports.DropDownItems.AddRange(New ToolStripItem() {
            Me.mnuRptInspections, Me.mnuRptViolations, Me.mnuRptStats})
        Me.mnuReports.Text = "التقارير"
        Me.mnuReports.ForeColor = Color.White
        '
        ' mnuRptInspections
        '
        Me.mnuRptInspections.Text = "تقرير التفتيشات"
        '
        ' mnuRptViolations
        '
        Me.mnuRptViolations.Text = "تقرير المخالفات"
        '
        ' mnuRptStats
        '
        Me.mnuRptStats.Text = "إحصائيات عامة"
        '
        ' mnuAdmin
        '
        Me.mnuAdmin.DropDownItems.AddRange(New ToolStripItem() {Me.mnuUsers})
        Me.mnuAdmin.Text = "إدارة النظام"
        Me.mnuAdmin.ForeColor = Color.White
        '
        ' mnuUsers
        '
        Me.mnuUsers.Text = "المستخدمون"
        '
        ' mnuHelp
        '
        Me.mnuHelp.DropDownItems.AddRange(New ToolStripItem() {Me.mnuAbout})
        Me.mnuHelp.Text = "مساعدة"
        Me.mnuHelp.ForeColor = Color.White
        '
        ' mnuAbout
        '
        Me.mnuAbout.Text = "عن البرنامج"
        '
        ' statusStrip1
        '
        Me.statusStrip1.Font = New Font("Tahoma", 10.0!)
        Me.statusStrip1.Items.AddRange(New ToolStripItem() {
            Me.lblUser, Me.lblRole, Me.lblSpring, Me.lblDate})
        Me.statusStrip1.Location = New Point(0, 678)
        Me.statusStrip1.RightToLeft = RightToLeft.Yes
        Me.statusStrip1.Size = New Size(1000, 22)
        '
        ' lblUser
        '
        Me.lblUser.Text = "المستخدم: "
        '
        ' lblRole
        '
        Me.lblRole.Text = "الصلاحية: "
        '
        ' lblSpring
        '
        Me.lblSpring.Spring = True
        '
        ' lblDate
        '
        Me.lblDate.Text = "التاريخ: "
        '
        ' pnlBackground
        '
        Me.pnlBackground.BackColor = Color.FromArgb(245, 247, 250)
        Me.pnlBackground.Controls.Add(Me.lblWelcome)
        Me.pnlBackground.Dock = DockStyle.Fill
        Me.pnlBackground.Location = New Point(0, 35)
        Me.pnlBackground.Size = New Size(1000, 643)
        '
        ' lblWelcome
        '
        Me.lblWelcome.Dock = DockStyle.Fill
        Me.lblWelcome.Font = New Font("Tahoma", 22.0!, FontStyle.Bold)
        Me.lblWelcome.ForeColor = Color.FromArgb(31, 78, 120)
        Me.lblWelcome.Text = "مرحباً بكم في برنامج تفتيش السلامة المهنية"
        Me.lblWelcome.TextAlign = ContentAlignment.MiddleCenter
        '
        ' tmrClock
        '
        Me.tmrClock.Interval = 1000
        Me.tmrClock.Enabled = True
        '
        ' FrmMain
        '
        Me.AutoScaleDimensions = New SizeF(7.0!, 15.0!)
        Me.AutoScaleMode = AutoScaleMode.Font
        Me.ClientSize = New Size(1000, 700)
        Me.Controls.Add(Me.pnlBackground)
        Me.Controls.Add(Me.statusStrip1)
        Me.Controls.Add(Me.menuStrip1)
        Me.IsMdiContainer = True
        Me.MainMenuStrip = Me.menuStrip1
        Me.Name = "FrmMain"
        Me.RightToLeft = RightToLeft.Yes
        Me.RightToLeftLayout = True
        Me.StartPosition = FormStartPosition.CenterScreen
        Me.Text = "برنامج تفتيش السلامة المهنية"
        Me.WindowState = FormWindowState.Maximized
        Me.menuStrip1.ResumeLayout(False)
        Me.menuStrip1.PerformLayout()
        Me.statusStrip1.ResumeLayout(False)
        Me.statusStrip1.PerformLayout()
        Me.pnlBackground.ResumeLayout(False)
        Me.ResumeLayout(False)
        Me.PerformLayout()
    End Sub

End Class
