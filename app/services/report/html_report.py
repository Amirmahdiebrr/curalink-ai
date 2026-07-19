"""
app/services/report/html_report.py

HTML report builder.
"""

from app.models.base_report import BaseMedicalReport


class HtmlReportBuilder:
    """
    Build HTML report from medical report model.
    """

    @staticmethod
    def build(
        report: BaseMedicalReport,
    ) -> str:

        findings = ""

        for finding in report.findings:

            findings += f"""
            <tr>
                <td>{finding.title}</td>
                <td>{finding.description}</td>
                <td>{finding.severity}</td>
            </tr>
            """

        parameters = ""

        for parameter in report.parameters:

            parameters += f"""
            <tr>
                <td>{parameter.name}</td>
                <td>{parameter.value or "-"}</td>
                <td>{parameter.unit or "-"}</td>
                <td>{parameter.reference_range or "-"}</td>
                <td>{parameter.status or "-"}</td>
            </tr>
            """

        recommendations = ""

        for recommendation in report.recommendations:

            recommendations += f"""
            <li>{recommendation.text}</li>
            """

        return f"""
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="utf-8">

<title>{report.title}</title>

<style>

body {{
    font-family: Arial, sans-serif;
    margin: 40px;
}}

table {{
    width:100%;
    border-collapse: collapse;
    margin-bottom:20px;
}}

th, td {{
    border:1px solid #ddd;
    padding:8px;
}}

th {{
    background:#f5f5f5;
}}

.summary {{
    background:#eef;
    padding:15px;
    margin-bottom:20px;
}}

</style>

</head>

<body>

<h1>{report.title}</h1>

<p><b>Document Type:</b> {report.document_type}</p>

<p><b>Confidence:</b> {report.confidence:.2f}</p>

<div class="summary">

<h2>Summary</h2>

<p>{report.summary}</p>

</div>

<h2>Parameters</h2>

<table>

<tr>

<th>Name</th>

<th>Value</th>

<th>Unit</th>

<th>Reference</th>

<th>Status</th>

</tr>

{parameters}

</table>

<h2>Findings</h2>

<table>

<tr>

<th>Finding</th>

<th>Description</th>

<th>Severity</th>

</tr>

{findings}

</table>

<h2>Recommendations</h2>

<ul>

{recommendations}

</ul>

</body>

</html>
"""