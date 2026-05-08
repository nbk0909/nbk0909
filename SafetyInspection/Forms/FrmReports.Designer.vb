<Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()>
Partial Class FrmReports
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

    Friend WithEvents pnlTop As Panel
    Friend WithEvents lblTitle As Label
    Friend WithEvents pnlFilter As Panel
    Friend WithEvents lblReport As Label
    Friend WithEvents cmbReport As ComboBox
    Friend WithEvents lblFromDate As Label
    Friend WithEvents dtpFromDate As DateTimePicker
    Friend WithEvents lblToDate As Label
    Friend WithEvents dtpToDate As DateTimePicker
    Friend WithEvents btnRun As Button
    Friend WithEvents btnExport As Button
    Friend WithEvents btnPrint As Button
    Friend WithEvents grdResults As DataGridView
    Friend WithEvents pnlStats As Panel
    Friend WithEvents lblStatsTitle As Label
    Friend WithEvents lblTotalEst As Label
    Friend WithEvents lblTotalInsp As Label
    Friend WithEvents lblTotalInspections As Label
    Friend WithEvents lblTotalViolations As Label
    Friend WithEvents lblTotalFines As Label

    <System.Diagnostics.DebuggerStepThrough()>
    Private Sub InitializeComponent()
        Me.pnlTop = New Panel() : Me.lblTitle = New Label()
        Me.pnlFilter = New Panel()
        Me.lblReport = New Label() : Me.cmbReport = New ComboBox()
        Me.lblFromDate = New Label() : Me.dtpFromDate = New DateTimePicker()
        Me.lblToDate = New Label() : Me.dtpToDate = New DateTimePicker()
        Me.btnRun = New Button() : Me.btnExport = New Button() : Me.btnPrint = New Button()
        Me.grdResults = New DataGridView()
        Me.pnlStats = New Panel()
        Me.lblStatsTitle = New Label()
        Me.lblTotalEst = New Label()
        Me.lblTotalInsp = New Label()
        Me.lblTotalInspections = New Label()
        Me.lblTotalViolations = New Label()
        Me.lblTotalFines = New Label()
        '
        Me.pnlTop.BackColor = Color.FromArgb(31, 78, 120)
        Me.pnlTop.Dock = DockStyle.Top : Me.pnlTop.Height = 50
        Me.lblTitle.Dock = DockStyle.Fill
        Me.lblTitle.Font = New Font("Tahoma", 14.0!, FontStyle.Bold)
        Me.lblTitle.ForeColor = Color.White
        Me.lblTitle.Text = "التقارير والإحصائيات"
        Me.lblTitle.TextAlign = ContentAlignment.MiddleCenter
        Me.pnlTop.Controls.Add(Me.lblTitle)
        '
        Me.pnlFilter.Dock = DockStyle.Top : Me.pnlFilter.Height = 70
        Me.pnlFilter.BackColor = Color.FromArgb(245, 247, 250)
        Me.pnlFilter.Padding = New Padding(10)
        '
        Me.lblReport.AutoSize = True : Me.lblReport.Font = New Font("Tahoma", 10.0!)
        Me.lblReport.Location = New Point(880, 25) : Me.lblReport.Text = "نوع التقرير:"
        Me.cmbReport.Location = New Point(620, 22) : Me.cmbReport.Size = New Size(250, 23)
        Me.cmbReport.Font = New Font("Tahoma", 10.0!)
        Me.cmbReport.DropDownStyle = ComboBoxStyle.DropDownList
        Me.cmbReport.Items.AddRange(New Object() {
            "تقرير التفتيشات", "تقرير المخالفات",
            "إحصائيات حسب القطاع", "إحصائيات حسب المفتش",
            "إحصائيات حسب درجة الخطورة"})
        Me.cmbReport.SelectedIndex = 0
        '
        Me.lblFromDate.AutoSize = True : Me.lblFromDate.Font = New Font("Tahoma", 10.0!)
        Me.lblFromDate.Location = New Point(560, 25) : Me.lblFromDate.Text = "من:"
        Me.dtpFromDate.Location = New Point(380, 22) : Me.dtpFromDate.Size = New Size(170, 23)
        Me.dtpFromDate.Font = New Font("Tahoma", 10.0!)
        Me.dtpFromDate.Format = DateTimePickerFormat.Short
        Me.dtpFromDate.Value = DateTime.Today.AddMonths(-3)
        '
        Me.lblToDate.AutoSize = True : Me.lblToDate.Font = New Font("Tahoma", 10.0!)
        Me.lblToDate.Location = New Point(330, 25) : Me.lblToDate.Text = "إلى:"
        Me.dtpToDate.Location = New Point(150, 22) : Me.dtpToDate.Size = New Size(170, 23)
        Me.dtpToDate.Font = New Font("Tahoma", 10.0!)
        Me.dtpToDate.Format = DateTimePickerFormat.Short
        '
        Me.btnRun.BackColor = Color.FromArgb(40, 167, 69) : Me.btnRun.FlatStyle = FlatStyle.Flat
        Me.btnRun.Font = New Font("Tahoma", 10.0!, FontStyle.Bold) : Me.btnRun.ForeColor = Color.White
        Me.btnRun.Location = New Point(20, 22) : Me.btnRun.Size = New Size(110, 28) : Me.btnRun.Text = "تشغيل"
        '
        Me.pnlFilter.Controls.AddRange(New Control() {
            Me.lblReport, Me.cmbReport, Me.lblFromDate, Me.dtpFromDate,
            Me.lblToDate, Me.dtpToDate, Me.btnRun})
        '
        Me.pnlStats.Dock = DockStyle.Bottom : Me.pnlStats.Height = 90
        Me.pnlStats.BackColor = Color.FromArgb(232, 240, 254)
        Me.pnlStats.Padding = New Padding(10)
        Me.lblStatsTitle.Font = New Font("Tahoma", 11.0!, FontStyle.Bold)
        Me.lblStatsTitle.ForeColor = Color.FromArgb(31, 78, 120)
        Me.lblStatsTitle.Text = "ملخص إحصائي:" : Me.lblStatsTitle.AutoSize = True
        Me.lblStatsTitle.Location = New Point(880, 12)
        Me.lblTotalEst.Font = New Font("Tahoma", 10.0!) : Me.lblTotalEst.AutoSize = True
        Me.lblTotalEst.Location = New Point(700, 45) : Me.lblTotalEst.Text = "المنشآت: 0"
        Me.lblTotalInsp.Font = New Font("Tahoma", 10.0!) : Me.lblTotalInsp.AutoSize = True
        Me.lblTotalInsp.Location = New Point(540, 45) : Me.lblTotalInsp.Text = "المفتشون: 0"
        Me.lblTotalInspections.Font = New Font("Tahoma", 10.0!) : Me.lblTotalInspections.AutoSize = True
        Me.lblTotalInspections.Location = New Point(360, 45) : Me.lblTotalInspections.Text = "التفتيشات: 0"
        Me.lblTotalViolations.Font = New Font("Tahoma", 10.0!) : Me.lblTotalViolations.AutoSize = True
        Me.lblTotalViolations.Location = New Point(180, 45) : Me.lblTotalViolations.Text = "المخالفات: 0"
        Me.lblTotalFines.Font = New Font("Tahoma", 10.0!, FontStyle.Bold)
        Me.lblTotalFines.ForeColor = Color.FromArgb(220, 53, 69)
        Me.lblTotalFines.AutoSize = True
        Me.lblTotalFines.Location = New Point(20, 45) : Me.lblTotalFines.Text = "إجمالي الغرامات: 0"
        Me.btnExport = New Button()
        Me.btnExport.BackColor = Color.FromArgb(0, 123, 255) : Me.btnExport.FlatStyle = FlatStyle.Flat
        Me.btnExport.Font = New Font("Tahoma", 10.0!, FontStyle.Bold) : Me.btnExport.ForeColor = Color.White
        Me.btnExport.Location = New Point(140, 22) : Me.btnExport.Size = New Size(120, 28) : Me.btnExport.Text = "تصدير CSV"
        Me.pnlFilter.Controls.Add(Me.btnExport)
        Me.btnPrint = New Button()
        Me.btnPrint.BackColor = Color.FromArgb(108, 117, 125) : Me.btnPrint.FlatStyle = FlatStyle.Flat
        Me.btnPrint.Font = New Font("Tahoma", 10.0!, FontStyle.Bold) : Me.btnPrint.ForeColor = Color.White
        Me.btnPrint.Location = New Point(270, 22) : Me.btnPrint.Size = New Size(90, 28) : Me.btnPrint.Text = "طباعة"
        Me.pnlFilter.Controls.Add(Me.btnPrint)
        Me.pnlStats.Controls.AddRange(New Control() {
            Me.lblStatsTitle, Me.lblTotalEst, Me.lblTotalInsp,
            Me.lblTotalInspections, Me.lblTotalViolations, Me.lblTotalFines})
        '
        Me.grdResults.AllowUserToAddRows = False
        Me.grdResults.AllowUserToDeleteRows = False
        Me.grdResults.BackgroundColor = Color.White
        Me.grdResults.BorderStyle = BorderStyle.None
        Me.grdResults.ColumnHeadersDefaultCellStyle.BackColor = Color.FromArgb(31, 78, 120)
        Me.grdResults.ColumnHeadersDefaultCellStyle.ForeColor = Color.White
        Me.grdResults.ColumnHeadersDefaultCellStyle.Font = New Font("Tahoma", 10.0!, FontStyle.Bold)
        Me.grdResults.ColumnHeadersHeight = 35
        Me.grdResults.Dock = DockStyle.Fill
        Me.grdResults.EnableHeadersVisualStyles = False
        Me.grdResults.Font = New Font("Tahoma", 10.0!)
        Me.grdResults.MultiSelect = False
        Me.grdResults.ReadOnly = True
        Me.grdResults.RowHeadersVisible = False
        Me.grdResults.RowTemplate.Height = 28
        Me.grdResults.SelectionMode = DataGridViewSelectionMode.FullRowSelect
        '
        Me.AutoScaleDimensions = New SizeF(7.0!, 15.0!)
        Me.AutoScaleMode = AutoScaleMode.Font
        Me.ClientSize = New Size(960, 640)
        Me.Controls.Add(Me.grdResults)
        Me.Controls.Add(Me.pnlStats)
        Me.Controls.Add(Me.pnlFilter)
        Me.Controls.Add(Me.pnlTop)
        Me.RightToLeft = RightToLeft.Yes
        Me.RightToLeftLayout = True
        Me.Text = "التقارير"
    End Sub

End Class
