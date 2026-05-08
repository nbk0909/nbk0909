''' <summary>
''' مدير الجلسة - يحفظ معلومات المستخدم الحالي في الذاكرة
''' </summary>
Public Class SessionManager

    Public Shared Property UserId As Integer = 0
    Public Shared Property Username As String = String.Empty
    Public Shared Property FullName As String = String.Empty
    Public Shared Property Role As String = String.Empty

    ''' <summary>هل المستخدم الحالي مدير النظام؟</summary>
    Public Shared ReadOnly Property IsAdmin As Boolean
        Get
            Return Role = "مدير"
        End Get
    End Property

    ''' <summary>إنهاء الجلسة الحالية</summary>
    Public Shared Sub Logout()
        UserId = 0
        Username = String.Empty
        FullName = String.Empty
        Role = String.Empty
    End Sub

End Class
