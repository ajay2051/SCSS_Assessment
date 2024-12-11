from django.urls import path

from extract.views import PdfTableExtractorView, PdfProcessingStatusView

urlpatterns = [
    path('extract-table/', PdfTableExtractorView.as_view(), name='extract-table'),
    path('status/<str:hash>/', PdfProcessingStatusView.as_view(), name='pdf-status'),
]
