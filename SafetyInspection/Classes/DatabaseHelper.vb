Imports System.Configuration
Imports System.Data
Imports System.Data.SqlClient
Imports System.Security.Cryptography
Imports System.Text

''' <summary>
''' فئة المساعد للتعامل مع قاعدة البيانات SQL Server
''' </summary>
Public Class DatabaseHelper

    Private Shared ReadOnly ConnectionString As String =
        ConfigurationManager.ConnectionStrings("SafetyInspectionDB").ConnectionString

    ''' <summary>إرجاع اتصال جديد بقاعدة البيانات</summary>
    Public Shared Function GetConnection() As SqlConnection
        Return New SqlConnection(ConnectionString)
    End Function

    ''' <summary>تنفيذ استعلام SELECT وإرجاع DataTable</summary>
    Public Shared Function ExecuteQuery(sql As String, ParamArray parameters As SqlParameter()) As DataTable
        Dim dt As New DataTable()
        Using conn As SqlConnection = GetConnection()
            Using cmd As New SqlCommand(sql, conn)
                If parameters IsNot Nothing AndAlso parameters.Length > 0 Then
                    cmd.Parameters.AddRange(parameters)
                End If
                Using adapter As New SqlDataAdapter(cmd)
                    adapter.Fill(dt)
                End Using
            End Using
        End Using
        Return dt
    End Function

    ''' <summary>تنفيذ أمر INSERT/UPDATE/DELETE وإرجاع عدد الصفوف المتأثرة</summary>
    Public Shared Function ExecuteNonQuery(sql As String, ParamArray parameters As SqlParameter()) As Integer
        Using conn As SqlConnection = GetConnection()
            conn.Open()
            Using cmd As New SqlCommand(sql, conn)
                If parameters IsNot Nothing AndAlso parameters.Length > 0 Then
                    cmd.Parameters.AddRange(parameters)
                End If
                Return cmd.ExecuteNonQuery()
            End Using
        End Using
    End Function

    ''' <summary>تنفيذ استعلام وإرجاع قيمة واحدة</summary>
    Public Shared Function ExecuteScalar(sql As String, ParamArray parameters As SqlParameter()) As Object
        Using conn As SqlConnection = GetConnection()
            conn.Open()
            Using cmd As New SqlCommand(sql, conn)
                If parameters IsNot Nothing AndAlso parameters.Length > 0 Then
                    cmd.Parameters.AddRange(parameters)
                End If
                Return cmd.ExecuteScalar()
            End Using
        End Using
    End Function

    ''' <summary>التحقق من إمكانية الاتصال بقاعدة البيانات</summary>
    Public Shared Function TestConnection() As Boolean
        Try
            Using conn As SqlConnection = GetConnection()
                conn.Open()
                Return conn.State = ConnectionState.Open
            End Using
        Catch
            Return False
        End Try
    End Function

    ''' <summary>تشفير كلمة المرور باستخدام SHA256</summary>
    Public Shared Function HashPassword(password As String) As String
        Using sha As SHA256 = SHA256.Create()
            Dim bytes = sha.ComputeHash(Encoding.UTF8.GetBytes(password))
            Dim sb As New StringBuilder()
            For Each b In bytes
                sb.Append(b.ToString("X2"))
            Next
            Return sb.ToString()
        End Using
    End Function

End Class
