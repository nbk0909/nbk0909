Imports System.Data
Imports System.Data.SqlClient
Imports System.Drawing.Printing
Imports System.IO
Imports System.Text

''' <summary>
''' شاشة التقارير والإحصائيات
''' </summary>
Public Class FrmReports

    Private Sub FrmReports_Load(sender As Object, e As EventArgs) Handles MyBase.Load
        dtpToDate.Value = DateTime.Today
        LoadStatistics()
        RunReport()
    End Sub

    Private Sub btnRun_Click(sender As Object, e As EventArgs) Handles btnRun.Click
        RunReport()
        LoadStatistics()
    End Sub

    Private Sub LoadStatistics()
        Try
            Dim fromDate = dtpFromDate.Value.Date
            Dim toDate = dtpToDate.Value.Date

            lblTotalEst.Text = "المنشآت: " &
                DatabaseHelper.ExecuteScalar("SELECT COUNT(*) FROM dbo.Establishments").ToString()
            lblTotalInsp.Text = "المفتشون: " &
                DatabaseHelper.ExecuteScalar("SELECT COUNT(*) FROM dbo.Inspectors WHERE IsActive=1").ToString()

            lblTotalInspections.Text = "التفتيشات: " &
                DatabaseHelper.ExecuteScalar(
                    "SELECT COUNT(*) FROM dbo.Inspections WHERE InspectionDate BETWEEN @f AND @t",
                    New SqlParameter("@f", fromDate),
                    New SqlParameter("@t", toDate)).ToString()

            lblTotalViolations.Text = "المخالفات: " &
                DatabaseHelper.ExecuteScalar(
                    "SELECT COUNT(*) FROM dbo.Violations v
                     INNER JOIN dbo.Inspections i ON i.InspectionId = v.InspectionId
                     WHERE i.InspectionDate BETWEEN @f AND @t",
                    New SqlParameter("@f", fromDate),
                    New SqlParameter("@t", toDate)).ToString()

            Dim fines = DatabaseHelper.ExecuteScalar(
                "SELECT ISNULL(SUM(v.FineAmount), 0) FROM dbo.Violations v
                 INNER JOIN dbo.Inspections i ON i.InspectionId = v.InspectionId
                 WHERE i.InspectionDate BETWEEN @f AND @t",
                New SqlParameter("@f", fromDate),
                New SqlParameter("@t", toDate))
            lblTotalFines.Text = "إجمالي الغرامات: " & CDec(fines).ToString("N2")

        Catch ex As Exception
            MessageBox.Show("خطأ في تحميل الإحصائيات: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub RunReport()
        Try
            Dim fromDate = dtpFromDate.Value.Date
            Dim toDate = dtpToDate.Value.Date
            Dim sql As String = ""

            Select Case cmbReport.SelectedIndex
                Case 0 ' تقرير التفتيشات
                    sql = "SELECT i.InspectionId AS [الرقم],
                                  e.EstablishmentName AS [المنشأة],
                                  e.Sector AS [القطاع], e.City AS [المدينة],
                                  ins.FullName AS [المفتش],
                                  i.InspectionDate AS [التاريخ],
                                  i.InspectionType AS [النوع],
                                  i.Status AS [الحالة],
                                  i.OverallRating AS [التقييم],
                                  (SELECT COUNT(*) FROM dbo.Violations v WHERE v.InspectionId = i.InspectionId) AS [عدد المخالفات]
                           FROM dbo.Inspections i
                           INNER JOIN dbo.Establishments e ON e.EstablishmentId = i.EstablishmentId
                           INNER JOIN dbo.Inspectors ins ON ins.InspectorId = i.InspectorId
                           WHERE i.InspectionDate BETWEEN @f AND @t
                           ORDER BY i.InspectionDate DESC"
                Case 1 ' تقرير المخالفات
                    sql = "SELECT v.ViolationId AS [الرقم],
                                  e.EstablishmentName AS [المنشأة],
                                  v.ViolationType AS [نوع المخالفة],
                                  v.Description AS [الوصف],
                                  v.Severity AS [الخطورة],
                                  v.FineAmount AS [الغرامة],
                                  v.Status AS [الحالة],
                                  i.InspectionDate AS [تاريخ التفتيش],
                                  v.CorrectionDeadline AS [موعد التصحيح]
                           FROM dbo.Violations v
                           INNER JOIN dbo.Inspections i ON i.InspectionId = v.InspectionId
                           INNER JOIN dbo.Establishments e ON e.EstablishmentId = i.EstablishmentId
                           WHERE i.InspectionDate BETWEEN @f AND @t
                           ORDER BY v.ViolationId DESC"
                Case 2 ' حسب القطاع
                    sql = "SELECT ISNULL(e.Sector, N'غير محدد') AS [القطاع],
                                  COUNT(DISTINCT e.EstablishmentId) AS [عدد المنشآت],
                                  COUNT(i.InspectionId) AS [عدد التفتيشات],
                                  ISNULL(SUM((SELECT COUNT(*) FROM dbo.Violations v WHERE v.InspectionId = i.InspectionId)), 0) AS [عدد المخالفات]
                           FROM dbo.Establishments e
                           LEFT JOIN dbo.Inspections i ON i.EstablishmentId = e.EstablishmentId
                                                       AND i.InspectionDate BETWEEN @f AND @t
                           GROUP BY e.Sector
                           ORDER BY [عدد التفتيشات] DESC"
                Case 3 ' حسب المفتش
                    sql = "SELECT ins.FullName AS [المفتش],
                                  ins.Specialization AS [التخصص],
                                  COUNT(i.InspectionId) AS [عدد التفتيشات],
                                  ISNULL(SUM((SELECT COUNT(*) FROM dbo.Violations v WHERE v.InspectionId = i.InspectionId)), 0) AS [عدد المخالفات],
                                  ISNULL(SUM((SELECT ISNULL(SUM(FineAmount),0) FROM dbo.Violations v WHERE v.InspectionId = i.InspectionId)), 0) AS [إجمالي الغرامات]
                           FROM dbo.Inspectors ins
                           LEFT JOIN dbo.Inspections i ON i.InspectorId = ins.InspectorId
                                                      AND i.InspectionDate BETWEEN @f AND @t
                           GROUP BY ins.FullName, ins.Specialization
                           ORDER BY [عدد التفتيشات] DESC"
                Case 4 ' حسب درجة الخطورة
                    sql = "SELECT v.Severity AS [درجة الخطورة],
                                  COUNT(*) AS [عدد المخالفات],
                                  ISNULL(SUM(v.FineAmount), 0) AS [إجمالي الغرامات],
                                  AVG(v.FineAmount) AS [متوسط الغرامة]
                           FROM dbo.Violations v
                           INNER JOIN dbo.Inspections i ON i.InspectionId = v.InspectionId
                           WHERE i.InspectionDate BETWEEN @f AND @t
                           GROUP BY v.Severity
                           ORDER BY [إجمالي الغرامات] DESC"
            End Select

            grdResults.DataSource = DatabaseHelper.ExecuteQuery(sql,
                New SqlParameter("@f", fromDate),
                New SqlParameter("@t", toDate))
        Catch ex As Exception
            MessageBox.Show("خطأ في توليد التقرير: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub btnExport_Click(sender As Object, e As EventArgs) Handles btnExport.Click
        If grdResults.RowCount = 0 Then
            MessageBox.Show("لا توجد بيانات للتصدير.", "تنبيه",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If

        Using sfd As New SaveFileDialog()
            sfd.Filter = "ملف CSV|*.csv"
            sfd.FileName = "تقرير_" & DateTime.Now.ToString("yyyyMMdd_HHmm") & ".csv"
            If sfd.ShowDialog() <> DialogResult.OK Then Return

            Try
                Dim sb As New StringBuilder()
                ' BOM لدعم العربية في Excel
                Dim headers As New List(Of String)
                For Each col As DataGridViewColumn In grdResults.Columns
                    headers.Add(EscapeCsv(col.HeaderText))
                Next
                sb.AppendLine(String.Join(",", headers))

                For Each row As DataGridViewRow In grdResults.Rows
                    Dim values As New List(Of String)
                    For Each cell As DataGridViewCell In row.Cells
                        values.Add(EscapeCsv(If(cell.Value Is Nothing, "", cell.Value.ToString())))
                    Next
                    sb.AppendLine(String.Join(",", values))
                Next

                File.WriteAllText(sfd.FileName, sb.ToString(), New UTF8Encoding(True))
                MessageBox.Show("تم التصدير بنجاح إلى:" & vbCrLf & sfd.FileName,
                                "نجاح", MessageBoxButtons.OK, MessageBoxIcon.Information)
            Catch ex As Exception
                MessageBox.Show("خطأ في التصدير: " & ex.Message, "خطأ",
                                MessageBoxButtons.OK, MessageBoxIcon.Error)
            End Try
        End Using
    End Sub

    Private Function EscapeCsv(value As String) As String
        If value Is Nothing Then Return ""
        If value.Contains(",") OrElse value.Contains("""") OrElse value.Contains(vbCrLf) Then
            Return """" & value.Replace("""", """""") & """"
        End If
        Return value
    End Function

    Private _printRowIndex As Integer
    Private Sub btnPrint_Click(sender As Object, e As EventArgs) Handles btnPrint.Click
        If grdResults.RowCount = 0 Then
            MessageBox.Show("لا توجد بيانات للطباعة.", "تنبيه",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If

        Try
            Using pd As New PrintDocument()
                _printRowIndex = 0
                AddHandler pd.PrintPage, AddressOf PrintDocPage
                Using ppd As New PrintPreviewDialog()
                    ppd.Document = pd
                    ppd.WindowState = FormWindowState.Maximized
                    ppd.ShowDialog()
                End Using
            End Using
        Catch ex As Exception
            MessageBox.Show("خطأ في الطباعة: " & ex.Message, "خطأ",
                            MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub PrintDocPage(sender As Object, e As PrintPageEventArgs)
        Dim titleFont As New Font("Tahoma", 14, FontStyle.Bold)
        Dim headerFont As New Font("Tahoma", 9, FontStyle.Bold)
        Dim cellFont As New Font("Tahoma", 8)
        Dim sf As New StringFormat() With {.Alignment = StringAlignment.Center}

        Dim x = e.MarginBounds.Left
        Dim y = e.MarginBounds.Top

        ' عنوان التقرير
        e.Graphics.DrawString(cmbReport.Text, titleFont, Brushes.DarkBlue,
                              New Rectangle(x, y, e.MarginBounds.Width, 30), sf)
        y += 35
        e.Graphics.DrawString(
            String.Format("الفترة: من {0:yyyy/MM/dd} إلى {1:yyyy/MM/dd}",
                          dtpFromDate.Value, dtpToDate.Value),
            cellFont, Brushes.Black,
            New Rectangle(x, y, e.MarginBounds.Width, 20), sf)
        y += 25

        Dim colCount = grdResults.Columns.Count
        Dim colWidth = e.MarginBounds.Width \ Math.Max(1, colCount)

        ' الترويسات
        Dim cx = x
        For Each col As DataGridViewColumn In grdResults.Columns
            e.Graphics.FillRectangle(Brushes.LightGray, cx, y, colWidth, 25)
            e.Graphics.DrawRectangle(Pens.Black, cx, y, colWidth, 25)
            e.Graphics.DrawString(col.HeaderText, headerFont, Brushes.Black,
                                  New Rectangle(cx, y + 4, colWidth, 20), sf)
            cx += colWidth
        Next
        y += 25

        ' الصفوف
        While _printRowIndex < grdResults.RowCount AndAlso y < e.MarginBounds.Bottom - 25
            cx = x
            Dim row = grdResults.Rows(_printRowIndex)
            For Each cell As DataGridViewCell In row.Cells
                e.Graphics.DrawRectangle(Pens.LightGray, cx, y, colWidth, 22)
                Dim val = If(cell.Value Is Nothing, "", cell.Value.ToString())
                e.Graphics.DrawString(val, cellFont, Brushes.Black,
                                      New Rectangle(cx + 2, y + 3, colWidth - 4, 20), sf)
                cx += colWidth
            Next
            y += 22
            _printRowIndex += 1
        End While

        e.HasMorePages = (_printRowIndex < grdResults.RowCount)
    End Sub

End Class
