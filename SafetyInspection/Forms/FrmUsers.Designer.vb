<Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()>
Partial Class FrmUsers
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
    Friend WithEvents grdUsers As DataGridView
    Friend WithEvents pnlForm As Panel
    Friend WithEvents lblUsername As Label : Friend WithEvents txtUsername As TextBox
    Friend WithEvents lblPassword As Label : Friend WithEvents txtPassword As TextBox
    Friend WithEvents lblFullName As Label : Friend WithEvents txtFullName As TextBox
    Friend WithEvents lblRole As Label : Friend WithEvents cmbRole As ComboBox
    Friend WithEvents chkActive As CheckBox
    Friend WithEvents lblHint As Label
    Friend WithEvents pnlButtons As Panel
    Friend WithEvents btnNew As Button : Friend WithEvents btnSave As Button
    Friend WithEvents btnDelete As Button : Friend WithEvents btnRefresh As Button

    <System.Diagnostics.DebuggerStepThrough()>
    Private Sub InitializeComponent()
        Me.pnlTop = New Panel() : Me.lblTitle = New Label()
        Me.grdUsers = New DataGridView()
        Me.pnlForm = New Panel()
        Me.lblUsername = New Label() : Me.txtUsername = New TextBox()
        Me.lblPassword = New Label() : Me.txtPassword = New TextBox()
        Me.lblFullName = New Label() : Me.txtFullName = New TextBox()
        Me.lblRole = New Label() : Me.cmbRole = New ComboBox()
        Me.chkActive = New CheckBox()
        Me.lblHint = New Label()
        Me.pnlButtons = New Panel()
        Me.btnNew = New Button() : Me.btnSave = New Button()
        Me.btnDelete = New Button() : Me.btnRefresh = New Button()
        '
        Me.pnlTop.BackColor = Color.FromArgb(31, 78, 120)
        Me.pnlTop.Dock = DockStyle.Top : Me.pnlTop.Height = 50
        Me.lblTitle.Dock = DockStyle.Fill
        Me.lblTitle.Font = New Font("Tahoma", 14.0!, FontStyle.Bold)
        Me.lblTitle.ForeColor = Color.White
        Me.lblTitle.Text = "إدارة المستخدمين"
        Me.lblTitle.TextAlign = ContentAlignment.MiddleCenter
        Me.pnlTop.Controls.Add(Me.lblTitle)
        '
        Me.grdUsers.AllowUserToAddRows = False
        Me.grdUsers.AllowUserToDeleteRows = False
        Me.grdUsers.BackgroundColor = Color.White
        Me.grdUsers.BorderStyle = BorderStyle.None
        Me.grdUsers.ColumnHeadersDefaultCellStyle.BackColor = Color.FromArgb(31, 78, 120)
        Me.grdUsers.ColumnHeadersDefaultCellStyle.ForeColor = Color.White
        Me.grdUsers.ColumnHeadersDefaultCellStyle.Font = New Font("Tahoma", 10.0!, FontStyle.Bold)
        Me.grdUsers.ColumnHeadersHeight = 35
        Me.grdUsers.Dock = DockStyle.Top
        Me.grdUsers.EnableHeadersVisualStyles = False
        Me.grdUsers.Font = New Font("Tahoma", 10.0!)
        Me.grdUsers.Height = 280
        Me.grdUsers.MultiSelect = False
        Me.grdUsers.ReadOnly = True
        Me.grdUsers.RowHeadersVisible = False
        Me.grdUsers.RowTemplate.Height = 28
        Me.grdUsers.SelectionMode = DataGridViewSelectionMode.FullRowSelect
        '
        Me.pnlForm.Dock = DockStyle.Fill
        Me.pnlForm.Padding = New Padding(15)
        '
        Me.lblUsername.AutoSize = True : Me.lblUsername.Font = New Font("Tahoma", 10.0!)
        Me.lblUsername.Location = New Point(620, 25) : Me.lblUsername.Text = "اسم المستخدم:"
        Me.txtUsername.Location = New Point(330, 22) : Me.txtUsername.Size = New Size(280, 23)
        Me.txtUsername.Font = New Font("Tahoma", 10.0!)
        '
        Me.lblPassword.AutoSize = True : Me.lblPassword.Font = New Font("Tahoma", 10.0!)
        Me.lblPassword.Location = New Point(620, 60) : Me.lblPassword.Text = "كلمة المرور:"
        Me.txtPassword.Location = New Point(330, 57) : Me.txtPassword.Size = New Size(280, 23)
        Me.txtPassword.Font = New Font("Tahoma", 10.0!) : Me.txtPassword.PasswordChar = "●"c
        '
        Me.lblFullName.AutoSize = True : Me.lblFullName.Font = New Font("Tahoma", 10.0!)
        Me.lblFullName.Location = New Point(620, 95) : Me.lblFullName.Text = "الاسم الكامل:"
        Me.txtFullName.Location = New Point(330, 92) : Me.txtFullName.Size = New Size(280, 23)
        Me.txtFullName.Font = New Font("Tahoma", 10.0!)
        '
        Me.lblRole.AutoSize = True : Me.lblRole.Font = New Font("Tahoma", 10.0!)
        Me.lblRole.Location = New Point(280, 25) : Me.lblRole.Text = "الصلاحية:"
        Me.cmbRole.Location = New Point(20, 22) : Me.cmbRole.Size = New Size(250, 23)
        Me.cmbRole.Font = New Font("Tahoma", 10.0!)
        Me.cmbRole.Items.AddRange(New Object() {"مدير", "مفتش", "مشرف", "موظف"})
        Me.cmbRole.SelectedIndex = 1
        '
        Me.chkActive.AutoSize = True : Me.chkActive.Font = New Font("Tahoma", 10.0!)
        Me.chkActive.Location = New Point(20, 65) : Me.chkActive.Text = "حساب نشط"
        Me.chkActive.Checked = True
        '
        Me.lblHint.AutoSize = True : Me.lblHint.Font = New Font("Tahoma", 9.0!, FontStyle.Italic)
        Me.lblHint.ForeColor = Color.Gray
        Me.lblHint.Location = New Point(20, 100)
        Me.lblHint.Text = "ملاحظة: عند التعديل اترك حقل كلمة المرور فارغاً للإبقاء على القديمة."
        '
        Me.pnlForm.Controls.AddRange(New Control() {
            Me.lblUsername, Me.txtUsername, Me.lblPassword, Me.txtPassword,
            Me.lblFullName, Me.txtFullName, Me.lblRole, Me.cmbRole,
            Me.chkActive, Me.lblHint})
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
        Me.Controls.Add(Me.grdUsers)
        Me.Controls.Add(Me.pnlTop)
        Me.RightToLeft = RightToLeft.Yes
        Me.RightToLeftLayout = True
        Me.Text = "إدارة المستخدمين"
    End Sub

End Class
