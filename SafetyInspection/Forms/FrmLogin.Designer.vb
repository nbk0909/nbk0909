<Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()>
Partial Class FrmLogin
    Inherits System.Windows.Forms.Form

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

    Private components As System.ComponentModel.IContainer

    Friend WithEvents pnlHeader As Panel
    Friend WithEvents lblTitle As Label
    Friend WithEvents lblSubTitle As Label
    Friend WithEvents lblUsername As Label
    Friend WithEvents lblPassword As Label
    Friend WithEvents txtUsername As TextBox
    Friend WithEvents txtPassword As TextBox
    Friend WithEvents btnLogin As Button
    Friend WithEvents btnExit As Button
    Friend WithEvents lblFooter As Label

    <System.Diagnostics.DebuggerStepThrough()>
    Private Sub InitializeComponent()
        Me.pnlHeader = New Panel()
        Me.lblTitle = New Label()
        Me.lblSubTitle = New Label()
        Me.lblUsername = New Label()
        Me.lblPassword = New Label()
        Me.txtUsername = New TextBox()
        Me.txtPassword = New TextBox()
        Me.btnLogin = New Button()
        Me.btnExit = New Button()
        Me.lblFooter = New Label()
        Me.pnlHeader.SuspendLayout()
        Me.SuspendLayout()
        '
        ' pnlHeader
        '
        Me.pnlHeader.BackColor = Color.FromArgb(31, 78, 120)
        Me.pnlHeader.Controls.Add(Me.lblSubTitle)
        Me.pnlHeader.Controls.Add(Me.lblTitle)
        Me.pnlHeader.Dock = DockStyle.Top
        Me.pnlHeader.Location = New Point(0, 0)
        Me.pnlHeader.Name = "pnlHeader"
        Me.pnlHeader.Size = New Size(450, 110)
        '
        ' lblTitle
        '
        Me.lblTitle.Dock = DockStyle.Top
        Me.lblTitle.Font = New Font("Tahoma", 18.0!, FontStyle.Bold)
        Me.lblTitle.ForeColor = Color.White
        Me.lblTitle.Location = New Point(0, 0)
        Me.lblTitle.Name = "lblTitle"
        Me.lblTitle.Size = New Size(450, 60)
        Me.lblTitle.TabIndex = 0
        Me.lblTitle.Text = "برنامج تفتيش السلامة المهنية"
        Me.lblTitle.TextAlign = ContentAlignment.MiddleCenter
        '
        ' lblSubTitle
        '
        Me.lblSubTitle.Dock = DockStyle.Bottom
        Me.lblSubTitle.Font = New Font("Tahoma", 10.0!)
        Me.lblSubTitle.ForeColor = Color.LightGray
        Me.lblSubTitle.Location = New Point(0, 70)
        Me.lblSubTitle.Name = "lblSubTitle"
        Me.lblSubTitle.Size = New Size(450, 40)
        Me.lblSubTitle.TabIndex = 1
        Me.lblSubTitle.Text = "تسجيل الدخول إلى النظام"
        Me.lblSubTitle.TextAlign = ContentAlignment.MiddleCenter
        '
        ' lblUsername
        '
        Me.lblUsername.AutoSize = True
        Me.lblUsername.Font = New Font("Tahoma", 11.0!)
        Me.lblUsername.Location = New Point(330, 145)
        Me.lblUsername.Name = "lblUsername"
        Me.lblUsername.Size = New Size(95, 19)
        Me.lblUsername.TabIndex = 1
        Me.lblUsername.Text = "اسم المستخدم:"
        '
        ' lblPassword
        '
        Me.lblPassword.AutoSize = True
        Me.lblPassword.Font = New Font("Tahoma", 11.0!)
        Me.lblPassword.Location = New Point(346, 200)
        Me.lblPassword.Name = "lblPassword"
        Me.lblPassword.Size = New Size(80, 19)
        Me.lblPassword.TabIndex = 3
        Me.lblPassword.Text = "كلمة المرور:"
        '
        ' txtUsername
        '
        Me.txtUsername.Font = New Font("Tahoma", 11.0!)
        Me.txtUsername.Location = New Point(50, 142)
        Me.txtUsername.Name = "txtUsername"
        Me.txtUsername.Size = New Size(275, 27)
        Me.txtUsername.TabIndex = 0
        Me.txtUsername.Text = "admin"
        Me.txtUsername.RightToLeft = RightToLeft.Yes
        '
        ' txtPassword
        '
        Me.txtPassword.Font = New Font("Tahoma", 11.0!)
        Me.txtPassword.Location = New Point(50, 197)
        Me.txtPassword.Name = "txtPassword"
        Me.txtPassword.PasswordChar = "●"c
        Me.txtPassword.Size = New Size(275, 27)
        Me.txtPassword.TabIndex = 1
        Me.txtPassword.RightToLeft = RightToLeft.Yes
        '
        ' btnLogin
        '
        Me.btnLogin.BackColor = Color.FromArgb(40, 167, 69)
        Me.btnLogin.FlatStyle = FlatStyle.Flat
        Me.btnLogin.Font = New Font("Tahoma", 11.0!, FontStyle.Bold)
        Me.btnLogin.ForeColor = Color.White
        Me.btnLogin.Location = New Point(225, 250)
        Me.btnLogin.Name = "btnLogin"
        Me.btnLogin.Size = New Size(135, 40)
        Me.btnLogin.TabIndex = 2
        Me.btnLogin.Text = "دخول"
        Me.btnLogin.UseVisualStyleBackColor = False
        '
        ' btnExit
        '
        Me.btnExit.BackColor = Color.FromArgb(220, 53, 69)
        Me.btnExit.FlatStyle = FlatStyle.Flat
        Me.btnExit.Font = New Font("Tahoma", 11.0!, FontStyle.Bold)
        Me.btnExit.ForeColor = Color.White
        Me.btnExit.Location = New Point(80, 250)
        Me.btnExit.Name = "btnExit"
        Me.btnExit.Size = New Size(135, 40)
        Me.btnExit.TabIndex = 3
        Me.btnExit.Text = "خروج"
        Me.btnExit.UseVisualStyleBackColor = False
        '
        ' lblFooter
        '
        Me.lblFooter.Dock = DockStyle.Bottom
        Me.lblFooter.Font = New Font("Tahoma", 9.0!)
        Me.lblFooter.ForeColor = Color.Gray
        Me.lblFooter.Location = New Point(0, 318)
        Me.lblFooter.Name = "lblFooter"
        Me.lblFooter.Size = New Size(450, 30)
        Me.lblFooter.TabIndex = 5
        Me.lblFooter.Text = "© 2026 - جميع الحقوق محفوظة"
        Me.lblFooter.TextAlign = ContentAlignment.MiddleCenter
        '
        ' FrmLogin
        '
        Me.AcceptButton = Me.btnLogin
        Me.AutoScaleDimensions = New SizeF(7.0!, 15.0!)
        Me.AutoScaleMode = AutoScaleMode.Font
        Me.BackColor = Color.White
        Me.CancelButton = Me.btnExit
        Me.ClientSize = New Size(450, 348)
        Me.Controls.Add(Me.lblFooter)
        Me.Controls.Add(Me.btnExit)
        Me.Controls.Add(Me.btnLogin)
        Me.Controls.Add(Me.txtPassword)
        Me.Controls.Add(Me.txtUsername)
        Me.Controls.Add(Me.lblPassword)
        Me.Controls.Add(Me.lblUsername)
        Me.Controls.Add(Me.pnlHeader)
        Me.FormBorderStyle = FormBorderStyle.FixedSingle
        Me.MaximizeBox = False
        Me.Name = "FrmLogin"
        Me.RightToLeft = RightToLeft.Yes
        Me.RightToLeftLayout = True
        Me.StartPosition = FormStartPosition.CenterScreen
        Me.Text = "تسجيل الدخول"
        Me.pnlHeader.ResumeLayout(False)
        Me.ResumeLayout(False)
        Me.PerformLayout()
    End Sub

End Class
