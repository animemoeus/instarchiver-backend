from rest_framework import serializers


class ProcessInstagramDataSerializer(serializers.Serializer):
    username = serializers.CharField()
    story_id = serializers.CharField()
    thumbnail = serializers.URLField()
    media = serializers.URLField()
    created_datetime = serializers.DateTimeField()
