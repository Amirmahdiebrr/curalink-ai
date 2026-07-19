"""
app/services/pdf/pdf_report.py

PDF report builder.
"""

from io import BytesIO

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.platypus import SimpleDocTemplate

from app.models.base_report import BaseMedicalReport


class PdfReportBuilder:
    """
    Build PDF report from medical report model.
    """

    @staticmethod
    def build(
        report: BaseMedicalReport,
    ) -> bytes:

        buffer = BytesIO()

        document = SimpleDocTemplate(
            buffer
        )

        styles = getSampleStyleSheet()

        elements = []

        elements.append(
            Paragraph(
                report.title,
                styles["Heading1"],
            )
        )

        elements.append(
            Paragraph(
                f"<b>Document Type:</b> {report.document_type}",
                styles["Normal"],
            )
        )

        elements.append(
            Paragraph(
                f"<b>Confidence:</b> {report.confidence:.2f}",
                styles["Normal"],
            )
        )

        elements.append(
            Paragraph(
                "<br/><b>Summary</b>",
                styles["Heading2"],
            )
        )

        elements.append(
            Paragraph(
                report.summary,
                styles["BodyText"],
            )
        )

        if report.parameters:

            elements.append(
                Paragraph(
                    "<br/><b>Parameters</b>",
                    styles["Heading2"],
                )
            )

            for parameter in report.parameters:

                elements.append(
                    Paragraph(
                        f"""
                        <b>{parameter.name}</b><br/>
                        Value: {parameter.value or "-"}<br/>
                        Unit: {parameter.unit or "-"}<br/>
                        Reference: {parameter.reference_range or "-"}<br/>
                        Status: {parameter.status or "-"}<br/>
                        Interpretation: {parameter.interpretation or "-"}
                        """,
                        styles["BodyText"],
                    )
                )

        if report.findings:

            elements.append(
                Paragraph(
                    "<br/><b>Findings</b>",
                    styles["Heading2"],
                )
            )

            for finding in report.findings:

                elements.append(
                    Paragraph(
                        f"""
                        <b>{finding.title}</b><br/>
                        {finding.description}<br/>
                        Severity: {finding.severity}
                        """,
                        styles["BodyText"],
                    )
                )

        if report.recommendations:

            elements.append(
                Paragraph(
                    "<br/><b>Recommendations</b>",
                    styles["Heading2"],
                )
            )

            for recommendation in report.recommendations:

                elements.append(
                    Paragraph(
                        f"• {recommendation.text}",
                        styles["BodyText"],
                    )
                )

        document.build(
            elements
        )

        pdf = buffer.getvalue()

        buffer.close()

        return pdf