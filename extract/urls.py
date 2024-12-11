from django.urls import path

from extract.views import PdfTableExtractorView

urlpatterns = [
    path('extract-table/', PdfTableExtractorView.as_view(), name='extract-table'),
]
