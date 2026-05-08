<Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()>
Partial Class FrmInspections
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
    Friend WithEvents grdInspections As DataGridView
    Friend WithEvents pnlForm As Panel
    Friend WithEvents lblEst As Label : Friend WithEvents cmbEst As ComboBox
    Friend WithEvents lblInsp As Label : Friend WithEvents cmbInsp As ComboBox
    Friend WithEvents lblDate As Label : Friend WithEvents dtpDate As DateTimePicker
    Friend WithEvents lblType As Label : Friend WithEvents cmbType As ComboBox
    Friend WithEvents lblStatus As Label : Friend WithEvents cmbStatus As ComboBox
    Friend WithEvents lblRating As Label : Friend WithEvents cmbRating As ComboBox
    Friend WithEvents lblNotes As Label : Friend WithEvents txtNotes As TextBox
    Friend WithEvents pnlButtons As Panel
    Friend WithEvents btnNew As Button
    Friend WithEvents btnSave As Button
    Friend WithEvents btnDelete As Button
    Friend WithEvents btnRefresh As Button
    Friend WithEvents btnViolations As Button

    <System.Diagnostics.DebuggerStepThrough()>
    Private Sub InitializeComponent()
        Me.pnlTop = New Panel() : Me.lblTitle = New Label()
        Me.grdInspections = New DataGridView()
        Me.pnlForm = New Panel()
        Me.lblEst = New Label() : Me.cmbEst = New ComboBox()
        Me.lblInsp = New Label() : Me.cmbInsp = New ComboBox()
        Me.lblDate = New Label() : Me.dtpDate = New DateTimePicker()
        Me.lblType = New Label() : Me.cmbType = New ComboBox()
        Me.lblStatus = New Label() : Me.cmbStatus = New ComboBox()
        Me.lblRating = New Label() : Me.cmbRating = New ComboBox()
        Me.lblNotes = New Label() : Me.txtNotes = New TextBox()
        Me.pnlButtons = New Panel()
        Me.btnNew = New Button() : Me.btnSave = New Button()
        Me.btnDelete = New Button() : Me.btnRefresh = New Button()
        Me.btnViolations = New Button()
        '
        Me.pnlTop.BackColor = Color.FromArgb(31, 78, 120)
        Me.pnlTop.Dock = DockStyle.Top : Me.pnlTop.Height = 50
        Me.lblTitle.Dock = DockStyle.Fill
        Me.lblTitle.Font = New Font("Tahoma", 14.0!, FontStyle.Bold)
        Me.lblTitle.ForeColor = Color.White
        Me.lblTitle.Text = "إدارة زيارات التفتيش"
        Me.lblTitle.TextAlign = ContentAlignment.MiddleCenter
        Me.pnlTop.Controls.Add(Me.lblTitle)
        '
        Me.grdInspections.AllowUserToAddRows = False
        Me.grdInspections.AllowUserToDeleteRows = False
        Me.grdInspections.BackgroundColor = Color.White
        Me.grdInspections.BorderStyle = BorderStyle.None
        Me.grdInspections.ColumnHeadersDefaultCellStyle.BackColor = Color.FromArgb(31, 78, 120)
        Me.grdInspections.ColumnHeadersDefaultCellStyle.ForeColor = Color.White
        Me.grdInspections.ColumnHeadersDefaultCellStyle.Font = New Font("Tahoma", 10.0!, FontStyle.Bold)
        Me.grdInspections.ColumnHeadersHeight = 35
        Me.grdInspections.Dock = DockStyle.Top
        Me.grdInspections.EnableHeadersVisualStyles = False
        Me.grdInspections.Font = New Font("Tahoma", 10.0!)
        Me.grdInspections.Height = 250
        Me.grdInspections.MultiSelect = False
        Me.grdInspections.ReadOnly = True
        Me.grdInspections.RowHeadersVisible = False
        Me.grdInspections.RowTemplate.Height = 28
        Me.grdInspections.SelectionMode = DataGridViewSelectionMode.FullRowSelect
        '
        Me.pnlForm.Dock = DockStyle.Fill
        Me.pnlForm.Padding = New Padding(15)
        '
        Me.lblEst.AutoSize = True : Me.lblEst.Font = New Font("Tahoma", 10.0!)
        Me.lblEst.Location = New Point(620, 25) : Me.lblEst.Text = "المنشأة:"
        Me.cmbEst.Location = New Point(330, 22) : Me.cmbEst.Size = New Size(280, 23)
        Me.cmbEst.Font = New Font("Tahoma", 10.0!)
        Me.cmbEst.DropDownStyle = ComboBoxStyle.DropDownList
        '
        Me.lblInsp.AutoSize = True : Me.lblInsp.Font = New Font("Tahoma", 10.0!)
        Me.lblInsp.Location = New Point(620, 60) : Me.lblInsp.Text = "المفتش:"
        Me.cmbInsp.Location = New Point(330, 57) : Me.cmbInsp.Size = New Size(280, 23)
        Me.cmbInsp.Font = New Font("Tahoma", 10.0!)
        Me.cmbInsp.DropDownStyle = ComboBoxStyle.DropDownList
        '
        Me.lblDate.AutoSize = True : Me.lblDate.Font = New Font("Tahoma", 10.0!)
        Me.lblDate.Location = New Point(620, 95) : Me.lblDate.Text = "تاريخ الزيارة:"
        Me.dtpDate.Location = New Point(330, 92) : Me.dtpDate.Size = New Size(280, 23)
        Me.dtpDate.Font = New Font("Tahoma", 10.0!) : Me.dtpDate.Format = DateTimePickerFormat.Short
        '
        Me.lblType.AutoSize = True : Me.lblType.Font = New Font("Tahoma", 10.0!)
        Me.lblType.Location = New Point(280, 25) : Me.lblType.Text = "نوع الزيارة:"
        Me.cmbType.Location = New Point(20, 22) : Me.cmbType.Size = New Size(250, 23)
        Me.cmbType.Font = New Font("Tahoma", 10.0!)
        Me.cmbType.Items.AddRange(New Object() {"دوري", "مفاجئ", "متابعة", "شكوى", "حادث"})
        Me.cmbType.SelectedIndex = 0
        '
        Me.lblStatus.AutoSize = True : Me.lblStatus.Font = New Font("Tahoma", 10.0!)
        Me.lblStatus.Location = New Point(280, 60) : Me.lblStatus.Text = "الحالة:"
        Me.cmbStatus.Location = New Point(20, 57) : Me.cmbStatus.Size = New Size(250, 23)
        Me.cmbStatus.Font = New Font("Tahoma", 10.0!)
        Me.cmbStatus.Items.AddRange(New Object() {"مفتوح", "قيد المراجعة", "مغلق", "ملغى"})
        Me.cmbStatus.SelectedIndex = 0
        '
        Me.lblRating.AutoSize = True : Me.lblRating.Font = New Font("Tahoma", 10.0!)
        Me.lblRating.Location = New Point(280, 95) : Me.lblRating.Text = "التقييم العام:"
        Me.cmbRating.Location = New Point(20, 92) : Me.cmbRating.Size = New Size(250, 23)
        Me.cmbRating.Font = New Font("Tahoma", 10.0!)
        Me.cmbRating.Items.AddRange(New Object() {"ممتاز", "جيد جداً", "جيد", "مقبول", "ضعيف"})
        '
        Me.lblNotes.AutoSize = True : Me.lblNotes.Font = New Font("Tahoma", 10.0!)
        Me.lblNotes.Location = New Point(620, 130) : Me.lblNotes.Text = "ملاحظات:"
        Me.txtNotes.Location = New Point(20, 130) : Me.txtNotes.Size = New Size(590, 70)
        Me.txtNotes.Font = New Font("Tahoma", 10.0!)
        Me.txtNotes.Multiline = True : Me.txtNotes.ScrollBars = ScrollBars.Vertical
        '
        Me.pnlForm.Controls.AddRange(New Control() {
            Me.lblEst, Me.cmbEst, Me.lblInsp, Me.cmbInsp,
            Me.lblDate, Me.dtpDate, Me.lblType, Me.cmbType,
            Me.lblStatus, Me.cmbStatus, Me.lblRating, Me.cmbRating,
            Me.lblNotes, Me.txtNotes})
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
        Me.btnViolations.BackColor = Color.FromArgb(255, 152, 0) : Me.btnViolations.FlatStyle = FlatStyle.Flat
        Me.btnViolations.Font = New Font("Tahoma", 10.0!, FontStyle.Bold) : Me.btnViolations.ForeColor = Color.White
        Me.btnViolations.Location = New Point(380, 12) : Me.btnViolations.Size = New Size(150, 36) : Me.btnViolations.Text = "إدارة المخالفات"
        Me.btnRefresh.BackColor = Color.FromArgb(0, 123, 255) : Me.btnRefresh.FlatStyle = FlatStyle.Flat
        Me.btnRefresh.Font = New Font("Tahoma", 10.0!, FontStyle.Bold) : Me.btnRefresh.ForeColor = Color.White
        Me.btnRefresh.Location = New Point(540, 12) : Me.btnRefresh.Size = New Size(110, 36) : Me.btnRefresh.Text = "تحديث"
        Me.pnlButtons.Controls.AddRange(New Control() {Me.btnNew, Me.btnSave, Me.btnDelete, Me.btnViolations, Me.btnRefresh})
        '
        Me.AutoScaleDimensions = New SizeF(7.0!, 15.0!)
        Me.AutoScaleMode = AutoScaleMode.Font
        Me.ClientSize = New Size(960, 640)
        Me.Controls.Add(Me.pnlForm)
        Me.Controls.Add(Me.pnlButtons)
        Me.Controls.Add(Me.grdInspections)
        Me.Controls.Add(Me.pnlTop)
        Me.RightToLeft = RightToLeft.Yes
        Me.RightToLeftLayout = True
        Me.Text = "إدارة التفتيشات"
    End Sub

End Class
