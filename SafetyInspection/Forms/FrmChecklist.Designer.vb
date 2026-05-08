<Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()>
Partial Class FrmChecklist
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
    Friend WithEvents grdItems As DataGridView
    Friend WithEvents pnlForm As Panel
    Friend WithEvents lblCategory As Label : Friend WithEvents cmbCategory As ComboBox
    Friend WithEvents lblItem As Label : Friend WithEvents txtItem As TextBox
    Friend WithEvents chkCritical As CheckBox
    Friend WithEvents chkActive As CheckBox
    Friend WithEvents pnlButtons As Panel
    Friend WithEvents btnNew As Button : Friend WithEvents btnSave As Button
    Friend WithEvents btnDelete As Button : Friend WithEvents btnRefresh As Button

    <System.Diagnostics.DebuggerStepThrough()>
    Private Sub InitializeComponent()
        Me.pnlTop = New Panel() : Me.lblTitle = New Label()
        Me.grdItems = New DataGridView()
        Me.pnlForm = New Panel()
        Me.lblCategory = New Label() : Me.cmbCategory = New ComboBox()
        Me.lblItem = New Label() : Me.txtItem = New TextBox()
        Me.chkCritical = New CheckBox() : Me.chkActive = New CheckBox()
        Me.pnlButtons = New Panel()
        Me.btnNew = New Button() : Me.btnSave = New Button()
        Me.btnDelete = New Button() : Me.btnRefresh = New Button()
        '
        Me.pnlTop.BackColor = Color.FromArgb(31, 78, 120)
        Me.pnlTop.Dock = DockStyle.Top : Me.pnlTop.Height = 50
        Me.lblTitle.Dock = DockStyle.Fill
        Me.lblTitle.Font = New Font("Tahoma", 14.0!, FontStyle.Bold)
        Me.lblTitle.ForeColor = Color.White
        Me.lblTitle.Text = "إدارة بنود قائمة الفحص"
        Me.lblTitle.TextAlign = ContentAlignment.MiddleCenter
        Me.pnlTop.Controls.Add(Me.lblTitle)
        '
        Me.grdItems.AllowUserToAddRows = False
        Me.grdItems.AllowUserToDeleteRows = False
        Me.grdItems.BackgroundColor = Color.White
        Me.grdItems.BorderStyle = BorderStyle.None
        Me.grdItems.ColumnHeadersDefaultCellStyle.BackColor = Color.FromArgb(31, 78, 120)
        Me.grdItems.ColumnHeadersDefaultCellStyle.ForeColor = Color.White
        Me.grdItems.ColumnHeadersDefaultCellStyle.Font = New Font("Tahoma", 10.0!, FontStyle.Bold)
        Me.grdItems.ColumnHeadersHeight = 35
        Me.grdItems.Dock = DockStyle.Top
        Me.grdItems.EnableHeadersVisualStyles = False
        Me.grdItems.Font = New Font("Tahoma", 10.0!)
        Me.grdItems.Height = 320
        Me.grdItems.MultiSelect = False
        Me.grdItems.ReadOnly = True
        Me.grdItems.RowHeadersVisible = False
        Me.grdItems.RowTemplate.Height = 28
        Me.grdItems.SelectionMode = DataGridViewSelectionMode.FullRowSelect
        '
        Me.pnlForm.Dock = DockStyle.Fill
        Me.pnlForm.Padding = New Padding(15)
        '
        Me.lblCategory.AutoSize = True : Me.lblCategory.Font = New Font("Tahoma", 10.0!)
        Me.lblCategory.Location = New Point(620, 25) : Me.lblCategory.Text = "الفئة:"
        Me.cmbCategory.Location = New Point(330, 22) : Me.cmbCategory.Size = New Size(280, 23)
        Me.cmbCategory.Font = New Font("Tahoma", 10.0!)
        Me.cmbCategory.Items.AddRange(New Object() {
            "الحماية من الحريق", "معدات الوقاية الشخصية", "الكهرباء",
            "بيئة العمل", "الإسعافات الأولية", "المواد الكيميائية",
            "الآلات والمعدات", "التدريب والتوعية"})
        '
        Me.lblItem.AutoSize = True : Me.lblItem.Font = New Font("Tahoma", 10.0!)
        Me.lblItem.Location = New Point(620, 60) : Me.lblItem.Text = "نص البند:"
        Me.txtItem.Location = New Point(20, 57) : Me.txtItem.Size = New Size(590, 50)
        Me.txtItem.Font = New Font("Tahoma", 10.0!)
        Me.txtItem.Multiline = True
        '
        Me.chkCritical.AutoSize = True : Me.chkCritical.Font = New Font("Tahoma", 10.0!)
        Me.chkCritical.Location = New Point(450, 120) : Me.chkCritical.Text = "بند حرج"
        Me.chkCritical.ForeColor = Color.FromArgb(220, 53, 69)
        '
        Me.chkActive.AutoSize = True : Me.chkActive.Font = New Font("Tahoma", 10.0!)
        Me.chkActive.Location = New Point(560, 120) : Me.chkActive.Text = "نشط"
        Me.chkActive.Checked = True
        '
        Me.pnlForm.Controls.AddRange(New Control() {
            Me.lblCategory, Me.cmbCategory, Me.lblItem, Me.txtItem,
            Me.chkCritical, Me.chkActive})
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
        Me.Controls.Add(Me.grdItems)
        Me.Controls.Add(Me.pnlTop)
        Me.RightToLeft = RightToLeft.Yes
        Me.RightToLeftLayout = True
        Me.Text = "بنود قائمة الفحص"
    End Sub

End Class
