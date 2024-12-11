from rest_framework import serializers


class PdfExtractResponseSerializer(serializers.Serializer):
    file_url = serializers.CharField()
    hash = serializers.CharField(max_length=1000)
    csv_url = serializers.CharField()
