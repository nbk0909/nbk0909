<Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()>
Partial Class FrmViolations
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
    Friend WithEvents lblFilterInsp As Label
    Friend WithEvents cmbFilterInsp As ComboBox
    Friend WithEvents grdViolations As DataGridView
    Friend WithEvents pnlForm As Panel
    Friend WithEvents lblInspection As Label : Friend WithEvents cmbInspection As ComboBox
    Friend WithEvents lblType As Label : Friend WithEvents cmbType As ComboBox
    Friend WithEvents lblDesc As Label : Friend WithEvents txtDesc As TextBox
    Friend WithEvents lblSeverity As Label : Friend WithEvents cmbSeverity As ComboBox
    Friend WithEvents lblFine As Label : Friend WithEvents numFine As NumericUpDown
    Friend WithEvents lblStatus As Label : Friend WithEvents cmbStatus As ComboBox
    Friend WithEvents lblDeadline As Label : Friend WithEvents dtpDeadline As DateTimePicker
    Friend WithEvents pnlButtons As Panel
    Friend WithEvents btnNew As Button
    Friend WithEvents btnSave As Button
    Friend WithEvents btnDelete As Button
    Friend WithEvents btnRefresh As Button

    <System.Diagnostics.DebuggerStepThrough()>
    Private Sub InitializeComponent()
        Me.pnlTop = New Panel() : Me.lblTitle = New Label()
        Me.lblFilterInsp = New Label() : Me.cmbFilterInsp = New ComboBox()
        Me.grdViolations = New DataGridView()
        Me.pnlForm = New Panel()
        Me.lblInspection = New Label() : Me.cmbInspection = New ComboBox()
        Me.lblType = New Label() : Me.cmbType = New ComboBox()
        Me.lblDesc = New Label() : Me.txtDesc = New TextBox()
        Me.lblSeverity = New Label() : Me.cmbSeverity = New ComboBox()
        Me.lblFine = New Label() : Me.numFine = New NumericUpDown()
        Me.lblStatus = New Label() : Me.cmbStatus = New ComboBox()
        Me.lblDeadline = New Label() : Me.dtpDeadline = New DateTimePicker()
        Me.pnlButtons = New Panel()
        Me.btnNew = New Button() : Me.btnSave = New Button()
        Me.btnDelete = New Button() : Me.btnRefresh = New Button()
        '
        Me.pnlTop.BackColor = Color.FromArgb(31, 78, 120)
        Me.pnlTop.Dock = DockStyle.Top : Me.pnlTop.Height = 90
        Me.lblTitle.Font = New Font("Tahoma", 14.0!, FontStyle.Bold)
        Me.lblTitle.ForeColor = Color.White : Me.lblTitle.Dock = DockStyle.Top : Me.lblTitle.Height = 45
        Me.lblTitle.Text = "إدارة المخالفات" : Me.lblTitle.TextAlign = ContentAlignment.MiddleCenter
        Me.lblFilterInsp.Font = New Font("Tahoma", 10.0!) : Me.lblFilterInsp.ForeColor = Color.White
        Me.lblFilterInsp.AutoSize = True : Me.lblFilterInsp.Location = New Point(620, 55)
        Me.lblFilterInsp.Text = "تصفية حسب التفتيش:"
        Me.cmbFilterInsp.Location = New Point(280, 52) : Me.cmbFilterInsp.Size = New Size(330, 23)
        Me.cmbFilterInsp.Font = New Font("Tahoma", 10.0!)
        Me.cmbFilterInsp.DropDownStyle = ComboBoxStyle.DropDownList
        Me.pnlTop.Controls.Add(Me.cmbFilterInsp)
        Me.pnlTop.Controls.Add(Me.lblFilterInsp)
        Me.pnlTop.Controls.Add(Me.lblTitle)
        '
        Me.grdViolations.AllowUserToAddRows = False
        Me.grdViolations.AllowUserToDeleteRows = False
        Me.grdViolations.BackgroundColor = Color.White
        Me.grdViolations.BorderStyle = BorderStyle.None
        Me.grdViolations.ColumnHeadersDefaultCellStyle.BackColor = Color.FromArgb(31, 78, 120)
        Me.grdViolations.ColumnHeadersDefaultCellStyle.ForeColor = Color.White
        Me.grdViolations.ColumnHeadersDefaultCellStyle.Font = New Font("Tahoma", 10.0!, FontStyle.Bold)
        Me.grdViolations.ColumnHeadersHeight = 35
        Me.grdViolations.Dock = DockStyle.Top
        Me.grdViolations.EnableHeadersVisualStyles = False
        Me.grdViolations.Font = New Font("Tahoma", 10.0!)
        Me.grdViolations.Height = 230
        Me.grdViolations.MultiSelect = False
        Me.grdViolations.ReadOnly = True
        Me.grdViolations.RowHeadersVisible = False
        Me.grdViolations.RowTemplate.Height = 28
        Me.grdViolations.SelectionMode = DataGridViewSelectionMode.FullRowSelect
        '
        Me.pnlForm.Dock = DockStyle.Fill
        Me.pnlForm.Padding = New Padding(15)
        '
        Me.lblInspection.AutoSize = True : Me.lblInspection.Font = New Font("Tahoma", 10.0!)
        Me.lblInspection.Location = New Point(620, 25) : Me.lblInspection.Text = "التفتيش:"
        Me.cmbInspection.Location = New Point(330, 22) : Me.cmbInspection.Size = New Size(280, 23)
        Me.cmbInspection.Font = New Font("Tahoma", 10.0!)
        Me.cmbInspection.DropDownStyle = ComboBoxStyle.DropDownList
        '
        Me.lblType.AutoSize = True : Me.lblType.Font = New Font("Tahoma", 10.0!)
        Me.lblType.Location = New Point(620, 60) : Me.lblType.Text = "نوع المخالفة:"
        Me.cmbType.Location = New Point(330, 57) : Me.cmbType.Size = New Size(280, 23)
        Me.cmbType.Font = New Font("Tahoma", 10.0!)
        Me.cmbType.Items.AddRange(New Object() {
            "عدم توفر معدات وقاية", "نقص في تجهيزات الحريق",
            "أسلاك كهربائية مكشوفة", "تخزين غير آمن للمواد",
            "عدم وجود مخارج طوارئ", "نقص في التدريب",
            "عدم نظافة بيئة العمل", "آلات بدون حواجز حماية", "أخرى"})
        '
        Me.lblDesc.AutoSize = True : Me.lblDesc.Font = New Font("Tahoma", 10.0!)
        Me.lblDesc.Location = New Point(620, 95) : Me.lblDesc.Text = "وصف المخالفة:"
        Me.txtDesc.Location = New Point(330, 92) : Me.txtDesc.Size = New Size(280, 70)
        Me.txtDesc.Font = New Font("Tahoma", 10.0!)
        Me.txtDesc.Multiline = True : Me.txtDesc.ScrollBars = ScrollBars.Vertical
        '
        Me.lblSeverity.AutoSize = True : Me.lblSeverity.Font = New Font("Tahoma", 10.0!)
        Me.lblSeverity.Location = New Point(280, 25) : Me.lblSeverity.Text = "درجة الخطورة:"
        Me.cmbSeverity.Location = New Point(20, 22) : Me.cmbSeverity.Size = New Size(250, 23)
        Me.cmbSeverity.Font = New Font("Tahoma", 10.0!)
        Me.cmbSeverity.Items.AddRange(New Object() {"بسيطة", "متوسطة", "خطيرة", "جسيمة"})
        Me.cmbSeverity.SelectedIndex = 1
        '
        Me.lblFine.AutoSize = True : Me.lblFine.Font = New Font("Tahoma", 10.0!)
        Me.lblFine.Location = New Point(280, 60) : Me.lblFine.Text = "قيمة الغرامة:"
        Me.numFine.Location = New Point(20, 57) : Me.numFine.Size = New Size(250, 23)
        Me.numFine.Font = New Font("Tahoma", 10.0!)
        Me.numFine.DecimalPlaces = 2
        Me.numFine.Maximum = 1000000
        Me.numFine.ThousandsSeparator = True
        '
        Me.lblStatus.AutoSize = True : Me.lblStatus.Font = New Font("Tahoma", 10.0!)
        Me.lblStatus.Location = New Point(280, 95) : Me.lblStatus.Text = "الحالة:"
        Me.cmbStatus.Location = New Point(20, 92) : Me.cmbStatus.Size = New Size(250, 23)
        Me.cmbStatus.Font = New Font("Tahoma", 10.0!)
        Me.cmbStatus.Items.AddRange(New Object() {"قائمة", "تم التصحيح", "ملغاة", "تحت المتابعة"})
        Me.cmbStatus.SelectedIndex = 0
        '
        Me.lblDeadline.AutoSize = True : Me.lblDeadline.Font = New Font("Tahoma", 10.0!)
        Me.lblDeadline.Location = New Point(280, 130) : Me.lblDeadline.Text = "تاريخ التصحيح:"
        Me.dtpDeadline.Location = New Point(20, 127) : Me.dtpDeadline.Size = New Size(250, 23)
        Me.dtpDeadline.Font = New Font("Tahoma", 10.0!)
        Me.dtpDeadline.Format = DateTimePickerFormat.Short
        Me.dtpDeadline.Value = DateTime.Today.AddDays(30)
        '
        Me.pnlForm.Controls.AddRange(New Control() {
            Me.lblInspection, Me.cmbInspection, Me.lblType, Me.cmbType,
            Me.lblDesc, Me.txtDesc, Me.lblSeverity, Me.cmbSeverity,
            Me.lblFine, Me.numFine, Me.lblStatus, Me.cmbStatus,
            Me.lblDeadline, Me.dtpDeadline})
        '
        Me.pnlButtons.Dock = DockStyle.Bottom : Me.pnlButtons.Height = 60
        Me.pnlButtons.BackColor = Color.FromArgb(245, 247, 250)
        Me.btnNew.BackColor = Color.FromArgb(108, 117, 125) : Me.btnNew.FlatStyle = FlatStyle.Flat
        Me.btnNew.Font = New Font("Tahoma", 10.0!, FontStyle.Bold) : Me.btnNew.ForeColor = Color.White
        Me.btnNew.Location = New Point(20, 12) : Me.btnNew.Size = New Size(110, 36) : Me.btnNew.Text = "جديد"
        Me.btnSave.BackColor = Color.FromArgb(40, 167, 69) : Me.btnSave.FlatStyle = FlatStyle.Flat
        Me.btnSave.Font = New Font("Tahoma", 10.0!, FontStyle.Bold) : Me.btnSave.ForeColor = Color.White
        Me.btnSave.Location = New Point(140, 12) : Me.btnSave.Size = New Size(110, 36) : Me.btnSave.Text = "حفظ"
        Me.btnDelete.BackColor = Color.FromArgb(220, 53, 69) : Me.btnDelete.FlatStyle = FlatStyle.Flat
        Me.btnDelete.Font = New Font("Tahoma", 10.0!, FontStyle.Bold) : Me.btnDelete.ForeColor = Color.White
        Me.btnDelete.Location = New Point(260, 12) : Me.btnDelete.Size = New Size(110, 36) : Me.btnDelete.Text = "حذف"
        Me.btnRefresh.BackColor = Color.FromArgb(0, 123, 255) : Me.btnRefresh.FlatStyle = FlatStyle.Flat
        Me.btnRefresh.Font = New Font("Tahoma", 10.0!, FontStyle.Bold) : Me.btnRefresh.ForeColor = Color.White
        Me.btnRefresh.Location = New Point(380, 12) : Me.btnRefresh.Size = New Size(110, 36) : Me.btnRefresh.Text = "تحديث"
        Me.pnlButtons.Controls.AddRange(New Control() {Me.btnNew, Me.btnSave, Me.btnDelete, Me.btnRefresh})
        '
        Me.AutoScaleDimensions = New SizeF(7.0!, 15.0!)
        Me.AutoScaleMode = AutoScaleMode.Font
        Me.ClientSize = New Size(960, 640)
        Me.Controls.Add(Me.pnlForm)
        Me.Controls.Add(Me.pnlButtons)
        Me.Controls.Add(Me.grdViolations)
        Me.Controls.Add(Me.pnlTop)
        Me.RightToLeft = RightToLeft.Yes
        Me.RightToLeftLayout = True
        Me.Text = "إدارة المخالفات"
    End Sub

End Class
