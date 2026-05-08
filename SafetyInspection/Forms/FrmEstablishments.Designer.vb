<Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()>
Partial Class FrmEstablishments
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
    Friend WithEvents pnlSearch As Panel
    Friend WithEvents txtSearch As TextBox
    Friend WithEvents lblSearch As Label
    Friend WithEvents grdEstablishments As DataGridView
    Friend WithEvents pnlForm As Panel
    Friend WithEvents lblName As Label
    Friend WithEvents txtName As TextBox
    Friend WithEvents lblRegNo As Label
    Friend WithEvents txtRegNo As TextBox
    Friend WithEvents lblSector As Label
    Friend WithEvents cmbSector As ComboBox
    Friend WithEvents lblActivity As Label
    Friend WithEvents txtActivity As TextBox
    Friend WithEvents lblAddress As Label
    Friend WithEvents txtAddress As TextBox
    Friend WithEvents lblCity As Label
    Friend WithEvents txtCity As TextBox
    Friend WithEvents lblPhone As Label
    Friend WithEvents txtPhone As TextBox
    Friend WithEvents lblEmail As Label
    Friend WithEvents txtEmail As TextBox
    Friend WithEvents lblOwner As Label
    Friend WithEvents txtOwner As TextBox
    Friend WithEvents lblEmpCount As Label
    Friend WithEvents numEmployees As NumericUpDown
    Friend WithEvents lblRisk As Label
    Friend WithEvents cmbRisk As ComboBox
    Friend WithEvents pnlButtons As Panel
    Friend WithEvents btnNew As Button
    Friend WithEvents btnSave As Button
    Friend WithEvents btnDelete As Button
    Friend WithEvents btnRefresh As Button

    <System.Diagnostics.DebuggerStepThrough()>
    Private Sub InitializeComponent()
        Me.pnlTop = New Panel()
        Me.lblTitle = New Label()
        Me.pnlSearch = New Panel()
        Me.txtSearch = New TextBox()
        Me.lblSearch = New Label()
        Me.grdEstablishments = New DataGridView()
        Me.pnlForm = New Panel()
        Me.lblName = New Label() : Me.txtName = New TextBox()
        Me.lblRegNo = New Label() : Me.txtRegNo = New TextBox()
        Me.lblSector = New Label() : Me.cmbSector = New ComboBox()
        Me.lblActivity = New Label() : Me.txtActivity = New TextBox()
        Me.lblAddress = New Label() : Me.txtAddress = New TextBox()
        Me.lblCity = New Label() : Me.txtCity = New TextBox()
        Me.lblPhone = New Label() : Me.txtPhone = New TextBox()
        Me.lblEmail = New Label() : Me.txtEmail = New TextBox()
        Me.lblOwner = New Label() : Me.txtOwner = New TextBox()
        Me.lblEmpCount = New Label() : Me.numEmployees = New NumericUpDown()
        Me.lblRisk = New Label() : Me.cmbRisk = New ComboBox()
        Me.pnlButtons = New Panel()
        Me.btnNew = New Button() : Me.btnSave = New Button()
        Me.btnDelete = New Button() : Me.btnRefresh = New Button()
        '
        ' pnlTop
        '
        Me.pnlTop.BackColor = Color.FromArgb(31, 78, 120)
        Me.pnlTop.Controls.Add(Me.lblTitle)
        Me.pnlTop.Dock = DockStyle.Top
        Me.pnlTop.Height = 50
        '
        ' lblTitle
        '
        Me.lblTitle.Dock = DockStyle.Fill
        Me.lblTitle.Font = New Font("Tahoma", 14.0!, FontStyle.Bold)
        Me.lblTitle.ForeColor = Color.White
        Me.lblTitle.Text = "إدارة المنشآت"
        Me.lblTitle.TextAlign = ContentAlignment.MiddleCenter
        '
        ' pnlSearch
        '
        Me.pnlSearch.Dock = DockStyle.Top
        Me.pnlSearch.Height = 45
        Me.pnlSearch.Padding = New Padding(10)
        Me.pnlSearch.Controls.Add(Me.txtSearch)
        Me.pnlSearch.Controls.Add(Me.lblSearch)
        '
        ' lblSearch
        '
        Me.lblSearch.AutoSize = True
        Me.lblSearch.Font = New Font("Tahoma", 10.0!)
        Me.lblSearch.Location = New Point(15, 15)
        Me.lblSearch.Text = "بحث:"
        '
        ' txtSearch
        '
        Me.txtSearch.Font = New Font("Tahoma", 10.0!)
        Me.txtSearch.Location = New Point(70, 12)
        Me.txtSearch.Size = New Size(300, 23)
        '
        ' grdEstablishments
        '
        Me.grdEstablishments.AllowUserToAddRows = False
        Me.grdEstablishments.AllowUserToDeleteRows = False
        Me.grdEstablishments.BackgroundColor = Color.White
        Me.grdEstablishments.BorderStyle = BorderStyle.None
        Me.grdEstablishments.ColumnHeadersDefaultCellStyle.BackColor = Color.FromArgb(31, 78, 120)
        Me.grdEstablishments.ColumnHeadersDefaultCellStyle.ForeColor = Color.White
        Me.grdEstablishments.ColumnHeadersDefaultCellStyle.Font = New Font("Tahoma", 10.0!, FontStyle.Bold)
        Me.grdEstablishments.ColumnHeadersHeight = 35
        Me.grdEstablishments.Dock = DockStyle.Top
        Me.grdEstablishments.EnableHeadersVisualStyles = False
        Me.grdEstablishments.Font = New Font("Tahoma", 10.0!)
        Me.grdEstablishments.Height = 230
        Me.grdEstablishments.MultiSelect = False
        Me.grdEstablishments.ReadOnly = True
        Me.grdEstablishments.RowHeadersVisible = False
        Me.grdEstablishments.RowTemplate.Height = 28
        Me.grdEstablishments.SelectionMode = DataGridViewSelectionMode.FullRowSelect
        '
        ' pnlForm
        '
        Me.pnlForm.Dock = DockStyle.Fill
        Me.pnlForm.AutoScroll = True
        Me.pnlForm.Padding = New Padding(15)
        '
        ' lblName/txtName (الاسم)
        '
        Me.lblName.AutoSize = True : Me.lblName.Font = New Font("Tahoma", 10.0!)
        Me.lblName.Location = New Point(620, 25) : Me.lblName.Text = "اسم المنشأة:"
        Me.txtName.Location = New Point(330, 22) : Me.txtName.Size = New Size(280, 23)
        Me.txtName.Font = New Font("Tahoma", 10.0!)
        '
        ' lblRegNo/txtRegNo (رقم السجل)
        '
        Me.lblRegNo.AutoSize = True : Me.lblRegNo.Font = New Font("Tahoma", 10.0!)
        Me.lblRegNo.Location = New Point(620, 60) : Me.lblRegNo.Text = "رقم السجل:"
        Me.txtRegNo.Location = New Point(330, 57) : Me.txtRegNo.Size = New Size(280, 23)
        Me.txtRegNo.Font = New Font("Tahoma", 10.0!)
        '
        ' lblSector/cmbSector (القطاع)
        '
        Me.lblSector.AutoSize = True : Me.lblSector.Font = New Font("Tahoma", 10.0!)
        Me.lblSector.Location = New Point(620, 95) : Me.lblSector.Text = "القطاع:"
        Me.cmbSector.Location = New Point(330, 92) : Me.cmbSector.Size = New Size(280, 23)
        Me.cmbSector.Font = New Font("Tahoma", 10.0!)
        Me.cmbSector.Items.AddRange(New Object() {"صناعي", "تجاري", "خدمي", "إنشاءات", "نقل", "زراعي", "صحي", "تعليمي"})
        '
        ' lblActivity/txtActivity (نوع النشاط)
        '
        Me.lblActivity.AutoSize = True : Me.lblActivity.Font = New Font("Tahoma", 10.0!)
        Me.lblActivity.Location = New Point(620, 130) : Me.lblActivity.Text = "نوع النشاط:"
        Me.txtActivity.Location = New Point(330, 127) : Me.txtActivity.Size = New Size(280, 23)
        Me.txtActivity.Font = New Font("Tahoma", 10.0!)
        '
        ' lblAddress/txtAddress (العنوان)
        '
        Me.lblAddress.AutoSize = True : Me.lblAddress.Font = New Font("Tahoma", 10.0!)
        Me.lblAddress.Location = New Point(620, 165) : Me.lblAddress.Text = "العنوان:"
        Me.txtAddress.Location = New Point(330, 162) : Me.txtAddress.Size = New Size(280, 23)
        Me.txtAddress.Font = New Font("Tahoma", 10.0!)
        '
        ' lblCity/txtCity (المدينة)
        '
        Me.lblCity.AutoSize = True : Me.lblCity.Font = New Font("Tahoma", 10.0!)
        Me.lblCity.Location = New Point(280, 25) : Me.lblCity.Text = "المدينة:"
        Me.txtCity.Location = New Point(20, 22) : Me.txtCity.Size = New Size(250, 23)
        Me.txtCity.Font = New Font("Tahoma", 10.0!)
        '
        ' lblPhone/txtPhone (الهاتف)
        '
        Me.lblPhone.AutoSize = True : Me.lblPhone.Font = New Font("Tahoma", 10.0!)
        Me.lblPhone.Location = New Point(280, 60) : Me.lblPhone.Text = "الهاتف:"
        Me.txtPhone.Location = New Point(20, 57) : Me.txtPhone.Size = New Size(250, 23)
        Me.txtPhone.Font = New Font("Tahoma", 10.0!)
        '
        ' lblEmail/txtEmail (البريد الإلكتروني)
        '
        Me.lblEmail.AutoSize = True : Me.lblEmail.Font = New Font("Tahoma", 10.0!)
        Me.lblEmail.Location = New Point(280, 95) : Me.lblEmail.Text = "البريد:"
        Me.txtEmail.Location = New Point(20, 92) : Me.txtEmail.Size = New Size(250, 23)
        Me.txtEmail.Font = New Font("Tahoma", 10.0!)
        '
        ' lblOwner/txtOwner (المالك)
        '
        Me.lblOwner.AutoSize = True : Me.lblOwner.Font = New Font("Tahoma", 10.0!)
        Me.lblOwner.Location = New Point(280, 130) : Me.lblOwner.Text = "اسم المالك:"
        Me.txtOwner.Location = New Point(20, 127) : Me.txtOwner.Size = New Size(250, 23)
        Me.txtOwner.Font = New Font("Tahoma", 10.0!)
        '
        ' lblEmpCount/numEmployees (عدد العاملين)
        '
        Me.lblEmpCount.AutoSize = True : Me.lblEmpCount.Font = New Font("Tahoma", 10.0!)
        Me.lblEmpCount.Location = New Point(280, 165) : Me.lblEmpCount.Text = "عدد العاملين:"
        Me.numEmployees.Location = New Point(20, 162) : Me.numEmployees.Size = New Size(120, 23)
        Me.numEmployees.Font = New Font("Tahoma", 10.0!)
        Me.numEmployees.Maximum = 100000
        '
        ' lblRisk/cmbRisk (مستوى المخاطرة)
        '
        Me.lblRisk.AutoSize = True : Me.lblRisk.Font = New Font("Tahoma", 10.0!)
        Me.lblRisk.Location = New Point(620, 200) : Me.lblRisk.Text = "مستوى المخاطر:"
        Me.cmbRisk.Location = New Point(330, 197) : Me.cmbRisk.Size = New Size(280, 23)
        Me.cmbRisk.Font = New Font("Tahoma", 10.0!)
        Me.cmbRisk.Items.AddRange(New Object() {"منخفض", "متوسط", "مرتفع", "عالي جداً"})
        Me.cmbRisk.SelectedIndex = 1
        '
        ' pnlButtons
        '
        Me.pnlButtons.Dock = DockStyle.Bottom
        Me.pnlButtons.Height = 60
        Me.pnlButtons.BackColor = Color.FromArgb(245, 247, 250)
        '
        ' btnNew
        '
        Me.btnNew.BackColor = Color.FromArgb(108, 117, 125)
        Me.btnNew.FlatStyle = FlatStyle.Flat
        Me.btnNew.Font = New Font("Tahoma", 10.0!, FontStyle.Bold)
        Me.btnNew.ForeColor = Color.White
        Me.btnNew.Location = New Point(20, 12)
        Me.btnNew.Size = New Size(110, 36)
        Me.btnNew.Text = "جديد"
        '
        ' btnSave
        '
        Me.btnSave.BackColor = Color.FromArgb(40, 167, 69)
        Me.btnSave.FlatStyle = FlatStyle.Flat
        Me.btnSave.Font = New Font("Tahoma", 10.0!, FontStyle.Bold)
        Me.btnSave.ForeColor = Color.White
        Me.btnSave.Location = New Point(140, 12)
        Me.btnSave.Size = New Size(110, 36)
        Me.btnSave.Text = "حفظ"
        '
        ' btnDelete
        '
        Me.btnDelete.BackColor = Color.FromArgb(220, 53, 69)
        Me.btnDelete.FlatStyle = FlatStyle.Flat
        Me.btnDelete.Font = New Font("Tahoma", 10.0!, FontStyle.Bold)
        Me.btnDelete.ForeColor = Color.White
        Me.btnDelete.Location = New Point(260, 12)
        Me.btnDelete.Size = New Size(110, 36)
        Me.btnDelete.Text = "حذف"
        '
        ' btnRefresh
        '
        Me.btnRefresh.BackColor = Color.FromArgb(0, 123, 255)
        Me.btnRefresh.FlatStyle = FlatStyle.Flat
        Me.btnRefresh.Font = New Font("Tahoma", 10.0!, FontStyle.Bold)
        Me.btnRefresh.ForeColor = Color.White
        Me.btnRefresh.Location = New Point(380, 12)
        Me.btnRefresh.Size = New Size(110, 36)
        Me.btnRefresh.Text = "تحديث"
        '
        Me.pnlButtons.Controls.Add(Me.btnNew)
        Me.pnlButtons.Controls.Add(Me.btnSave)
        Me.pnlButtons.Controls.Add(Me.btnDelete)
        Me.pnlButtons.Controls.Add(Me.btnRefresh)

        Me.pnlForm.Controls.AddRange(New Control() {
            Me.lblName, Me.txtName, Me.lblRegNo, Me.txtRegNo,
            Me.lblSector, Me.cmbSector, Me.lblActivity, Me.txtActivity,
            Me.lblAddress, Me.txtAddress, Me.lblCity, Me.txtCity,
            Me.lblPhone, Me.txtPhone, Me.lblEmail, Me.txtEmail,
            Me.lblOwner, Me.txtOwner, Me.lblEmpCount, Me.numEmployees,
            Me.lblRisk, Me.cmbRisk})

        '
        ' FrmEstablishments
        '
        Me.AutoScaleDimensions = New SizeF(7.0!, 15.0!)
        Me.AutoScaleMode = AutoScaleMode.Font
        Me.ClientSize = New Size(960, 640)
        Me.Controls.Add(Me.pnlForm)
        Me.Controls.Add(Me.pnlButtons)
        Me.Controls.Add(Me.grdEstablishments)
        Me.Controls.Add(Me.pnlSearch)
        Me.Controls.Add(Me.pnlTop)
        Me.RightToLeft = RightToLeft.Yes
        Me.RightToLeftLayout = True
        Me.Text = "إدارة المنشآت"
    End Sub

End Class
