from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Pet, PetState, PetEvent


class PetAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", password="pass")
        self.pet = Pet.objects.create(name="Mochi", skin="gato")
        PetState.objects.create(pet=self.pet, mood="alegre", energy=80, happiness=90)

    def test_list_pets_public(self):
        res = self.client.get("/api/pets/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)

    def test_create_pet_requires_auth(self):
        res = self.client.post("/api/pets/", {"name": "Novo"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_pet_authenticated(self):
        self.client.force_authenticate(self.user)
        res = self.client.post("/api/pets/", {"name": "PetNovo", "skin": "robo"})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["name"], "PetNovo")

    def test_sync_updates_state(self):
        self.client.force_authenticate(self.user)
        payload = {
            "mood": "agitado",
            "energy": 60,
            "happiness": 70,
            "days_offline": 1,
            "event_type": "play",
        }
        res = self.client.post(f"/api/pets/{self.pet.id}/sync/", payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.pet.state.refresh_from_db()
        self.assertEqual(self.pet.state.mood, "agitado")
        self.assertEqual(PetEvent.objects.filter(pet=self.pet, event_type="play").count(), 1)

    def test_pet_events_list(self):
        PetEvent.objects.create(pet=self.pet, event_type="boot")
        res = self.client.get(f"/api/pets/{self.pet.id}/events/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
