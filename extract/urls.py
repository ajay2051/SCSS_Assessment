from django.urls import path

from extract.views import PDFDetailView, PDFListView, PDFUploadView

urlpatterns = [
    path('pdfs/', PDFListView.as_view(), name='pdf-list'),
    path('pdfs/upload/', PDFUploadView.as_view(), name='pdf-upload'),
    path('pdfs/<uuid:pk>/', PDFDetailView.as_view(), name='pdf-detail'),
]
