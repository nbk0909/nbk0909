<Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()>
Partial Class FrmInspectors
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
    Friend WithEvents grdInspectors As DataGridView
    Friend WithEvents pnlForm As Panel
    Friend WithEvents lblEmpNo As Label : Friend WithEvents txtEmpNo As TextBox
    Friend WithEvents lblName As Label : Friend WithEvents txtName As TextBox
    Friend WithEvents lblNationalId As Label : Friend WithEvents txtNationalId As TextBox
    Friend WithEvents lblSpec As Label : Friend WithEvents cmbSpec As ComboBox
    Friend WithEvents lblPhone As Label : Friend WithEvents txtPhone As TextBox
    Friend WithEvents lblEmail As Label : Friend WithEvents txtEmail As TextBox
    Friend WithEvents lblHire As Label : Friend WithEvents dtpHire As DateTimePicker
    Friend WithEvents chkActive As CheckBox
    Friend WithEvents pnlButtons As Panel
    Friend WithEvents btnNew As Button
    Friend WithEvents btnSave As Button
    Friend WithEvents btnDelete As Button
    Friend WithEvents btnRefresh As Button

    <System.Diagnostics.DebuggerStepThrough()>
    Private Sub InitializeComponent()
        Me.pnlTop = New Panel() : Me.lblTitle = New Label()
        Me.grdInspectors = New DataGridView()
        Me.pnlForm = New Panel()
        Me.lblEmpNo = New Label() : Me.txtEmpNo = New TextBox()
        Me.lblName = New Label() : Me.txtName = New TextBox()
        Me.lblNationalId = New Label() : Me.txtNationalId = New TextBox()
        Me.lblSpec = New Label() : Me.cmbSpec = New ComboBox()
        Me.lblPhone = New Label() : Me.txtPhone = New TextBox()
        Me.lblEmail = New Label() : Me.txtEmail = New TextBox()
        Me.lblHire = New Label() : Me.dtpHire = New DateTimePicker()
        Me.chkActive = New CheckBox()
        Me.pnlButtons = New Panel()
        Me.btnNew = New Button() : Me.btnSave = New Button()
        Me.btnDelete = New Button() : Me.btnRefresh = New Button()
        '
        ' pnlTop
        '
        Me.pnlTop.BackColor = Color.FromArgb(31, 78, 120)
        Me.pnlTop.Dock = DockStyle.Top
        Me.pnlTop.Height = 50
        Me.lblTitle.Dock = DockStyle.Fill
        Me.lblTitle.Font = New Font("Tahoma", 14.0!, FontStyle.Bold)
        Me.lblTitle.ForeColor = Color.White
        Me.lblTitle.Text = "إدارة المفتشين"
        Me.lblTitle.TextAlign = ContentAlignment.MiddleCenter
        Me.pnlTop.Controls.Add(Me.lblTitle)
        '
        ' grdInspectors
        '
        Me.grdInspectors.AllowUserToAddRows = False
        Me.grdInspectors.AllowUserToDeleteRows = False
        Me.grdInspectors.BackgroundColor = Color.White
        Me.grdInspectors.BorderStyle = BorderStyle.None
        Me.grdInspectors.ColumnHeadersDefaultCellStyle.BackColor = Color.FromArgb(31, 78, 120)
        Me.grdInspectors.ColumnHeadersDefaultCellStyle.ForeColor = Color.White
        Me.grdInspectors.ColumnHeadersDefaultCellStyle.Font = New Font("Tahoma", 10.0!, FontStyle.Bold)
        Me.grdInspectors.ColumnHeadersHeight = 35
        Me.grdInspectors.Dock = DockStyle.Top
        Me.grdInspectors.EnableHeadersVisualStyles = False
        Me.grdInspectors.Font = New Font("Tahoma", 10.0!)
        Me.grdInspectors.Height = 250
        Me.grdInspectors.MultiSelect = False
        Me.grdInspectors.ReadOnly = True
        Me.grdInspectors.RowHeadersVisible = False
        Me.grdInspectors.RowTemplate.Height = 28
        Me.grdInspectors.SelectionMode = DataGridViewSelectionMode.FullRowSelect
        '
        ' pnlForm
        '
        Me.pnlForm.Dock = DockStyle.Fill
        Me.pnlForm.Padding = New Padding(15)
        '
        Me.lblEmpNo.AutoSize = True : Me.lblEmpNo.Font = New Font("Tahoma", 10.0!)
        Me.lblEmpNo.Location = New Point(620, 25) : Me.lblEmpNo.Text = "الرقم الوظيفي:"
        Me.txtEmpNo.Location = New Point(330, 22) : Me.txtEmpNo.Size = New Size(280, 23)
        Me.txtEmpNo.Font = New Font("Tahoma", 10.0!)

        Me.lblName.AutoSize = True : Me.lblName.Font = New Font("Tahoma", 10.0!)
        Me.lblName.Location = New Point(620, 60) : Me.lblName.Text = "الاسم الكامل:"
        Me.txtName.Location = New Point(330, 57) : Me.txtName.Size = New Size(280, 23)
        Me.txtName.Font = New Font("Tahoma", 10.0!)

        Me.lblNationalId.AutoSize = True : Me.lblNationalId.Font = New Font("Tahoma", 10.0!)
        Me.lblNationalId.Location = New Point(620, 95) : Me.lblNationalId.Text = "الرقم القومي:"
        Me.txtNationalId.Location = New Point(330, 92) : Me.txtNationalId.Size = New Size(280, 23)
        Me.txtNationalId.Font = New Font("Tahoma", 10.0!)

        Me.lblSpec.AutoSize = True : Me.lblSpec.Font = New Font("Tahoma", 10.0!)
        Me.lblSpec.Location = New Point(620, 130) : Me.lblSpec.Text = "التخصص:"
        Me.cmbSpec.Location = New Point(330, 127) : Me.cmbSpec.Size = New Size(280, 23)
        Me.cmbSpec.Font = New Font("Tahoma", 10.0!)
        Me.cmbSpec.Items.AddRange(New Object() {
            "السلامة الصناعية", "الصحة المهنية", "الحماية من الحريق",
            "السلامة الكهربائية", "السلامة الكيميائية", "هندسة بيئية"})

        Me.lblPhone.AutoSize = True : Me.lblPhone.Font = New Font("Tahoma", 10.0!)
        Me.lblPhone.Location = New Point(280, 25) : Me.lblPhone.Text = "الهاتف:"
        Me.txtPhone.Location = New Point(20, 22) : Me.txtPhone.Size = New Size(250, 23)
        Me.txtPhone.Font = New Font("Tahoma", 10.0!)

        Me.lblEmail.AutoSize = True : Me.lblEmail.Font = New Font("Tahoma", 10.0!)
        Me.lblEmail.Location = New Point(280, 60) : Me.lblEmail.Text = "البريد الإلكتروني:"
        Me.txtEmail.Location = New Point(20, 57) : Me.txtEmail.Size = New Size(250, 23)
        Me.txtEmail.Font = New Font("Tahoma", 10.0!)

        Me.lblHire.AutoSize = True : Me.lblHire.Font = New Font("Tahoma", 10.0!)
        Me.lblHire.Location = New Point(280, 95) : Me.lblHire.Text = "تاريخ التعيين:"
        Me.dtpHire.Location = New Point(20, 92) : Me.dtpHire.Size = New Size(250, 23)
        Me.dtpHire.Font = New Font("Tahoma", 10.0!) : Me.dtpHire.Format = DateTimePickerFormat.Short

        Me.chkActive.AutoSize = True
        Me.chkActive.Font = New Font("Tahoma", 10.0!)
        Me.chkActive.Location = New Point(20, 130)
        Me.chkActive.Text = "نشط"
        Me.chkActive.Checked = True

        Me.pnlForm.Controls.AddRange(New Control() {
            Me.lblEmpNo, Me.txtEmpNo, Me.lblName, Me.txtName,
            Me.lblNationalId, Me.txtNationalId, Me.lblSpec, Me.cmbSpec,
            Me.lblPhone, Me.txtPhone, Me.lblEmail, Me.txtEmail,
            Me.lblHire, Me.dtpHire, Me.chkActive})
        '
        ' pnlButtons
        '
        Me.pnlButtons.Dock = DockStyle.Bottom
        Me.pnlButtons.Height = 60
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
        ' FrmInspectors
        '
        Me.AutoScaleDimensions = New SizeF(7.0!, 15.0!)
        Me.AutoScaleMode = AutoScaleMode.Font
        Me.ClientSize = New Size(960, 640)
        Me.Controls.Add(Me.pnlForm)
        Me.Controls.Add(Me.pnlButtons)
        Me.Controls.Add(Me.grdInspectors)
        Me.Controls.Add(Me.pnlTop)
        Me.RightToLeft = RightToLeft.Yes
        Me.RightToLeftLayout = True
        Me.Text = "إدارة المفتشين"
    End Sub

End Class
