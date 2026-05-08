Imports System.Globalization
Imports System.Threading
Imports System.Windows.Forms

Public Module Program

    <STAThread()>
    Public Sub Main()
        Application.EnableVisualStyles()
        Application.SetCompatibleTextRenderingDefault(False)

        ' ضبط الواجهة على اللغة العربية
        Dim arCulture As New CultureInfo("ar-SA")
        Thread.CurrentThread.CurrentCulture = arCulture
        Thread.CurrentThread.CurrentUICulture = arCulture
        Application.CurrentCulture = arCulture

        ' عرض شاشة الدخول
        Dim login As New FrmLogin()
        If login.ShowDialog() = DialogResult.OK Then
            Application.Run(New FrmMain())
        End If
    End Sub

End Module
