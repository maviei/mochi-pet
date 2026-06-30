from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Pet, PetState, PetEvent
from .serializers import PetSerializer, PetStateSerializer, PetEventSerializer, SyncSerializer


class PetViewSet(viewsets.ModelViewSet):
    serializer_class = PetSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return Pet.objects.select_related("state").all()

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def sync(self, request, pk=None):
        """Endpoint chamado pelo BitDogLab para sincronizar estado."""
        pet = get_object_or_404(Pet, pk=pk)
        serializer = SyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        state, _ = PetState.objects.update_or_create(
            pet=pet,
            defaults={
                "mood": data["mood"],
                "energy": data["energy"],
                "happiness": data["happiness"],
                "days_offline": data["days_offline"],
            },
        )

        if data.get("skin"):
            pet.skin = data["skin"]
            pet.save(update_fields=["skin"])

        if data.get("event_type"):
            PetEvent.objects.create(
                pet=pet,
                event_type=data["event_type"],
                detail=data.get("event_detail", {}),
            )

        return Response(PetSerializer(pet).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def events(self, request, pk=None):
        pet = get_object_or_404(Pet, pk=pk)
        qs = PetEvent.objects.filter(pet=pet).select_related("pet")
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(PetEventSerializer(page, many=True).data)
        return Response(PetEventSerializer(qs, many=True).data)


class PetEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PetEventSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return PetEvent.objects.select_related("pet").all()
