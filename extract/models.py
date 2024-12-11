from django.db import models


class Pdf(models.Model):
    file = models.FileField(upload_to='pdfs/%Y/%m/%d/')
    hash = models.CharField(max_length=1000, unique=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PDF {self.hash[:8]}..." # Displaying the first 8 characters of the hash


class CsvFile(models.Model):
    pdf = models.ForeignKey(Pdf, on_delete=models.CASCADE, related_name='csv_files')
    file = models.FileField(max_length=1000, upload_to='csvs/%Y/%m/%d/')
    extracted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"CSV for {self.pdf.hash[:8]}..."
