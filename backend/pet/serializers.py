from rest_framework import serializers
from .models import Pet, PetState, PetEvent


class PetStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetState
        fields = ["mood", "energy", "happiness", "days_offline", "last_seen"]
        read_only_fields = ["last_seen"]

    def validate_energy(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError("Energia deve estar entre 0 e 100.")
        return value

    def validate_happiness(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError("Felicidade deve estar entre 0 e 100.")
        return value


class PetSerializer(serializers.ModelSerializer):
    state = PetStateSerializer(read_only=True)

    class Meta:
        model = Pet
        fields = ["id", "name", "skin", "created_at", "state"]
        read_only_fields = ["created_at"]


class PetEventSerializer(serializers.ModelSerializer):
    pet_name = serializers.CharField(source="pet.name", read_only=True)

    class Meta:
        model = PetEvent
        fields = ["id", "pet", "pet_name", "event_type", "detail", "occurred_at"]
        read_only_fields = ["occurred_at"]


class SyncSerializer(serializers.Serializer):
    """Recebe o estado atual do BitDogLab e persiste atomicamente."""
    mood = serializers.ChoiceField(choices=PetState.MOOD_CHOICES)
    energy = serializers.IntegerField(min_value=0, max_value=100)
    happiness = serializers.IntegerField(min_value=0, max_value=100)
    days_offline = serializers.IntegerField(min_value=0)
    skin = serializers.ChoiceField(choices=Pet.SKIN_CHOICES, required=False)
    event_type = serializers.ChoiceField(choices=PetEvent.EVENT_CHOICES, required=False)
    event_detail = serializers.JSONField(default=dict, required=False)
