from django.db import models


class Pet(models.Model):
    SKIN_CHOICES = [
        ("classico", "Clássico"),
        ("kawaii", "Kawaii"),
        ("robo", "Robô"),
        ("gato", "Gato"),
    ]

    name = models.CharField(max_length=64, default="MochiPet")
    skin = models.CharField(max_length=16, choices=SKIN_CHOICES, default="classico")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PetState(models.Model):
    MOOD_CHOICES = [
        ("alegre", "Alegre"),
        ("serio", "Sério"),
        ("timido", "Tímido"),
        ("agitado", "Agitado"),
    ]

    pet = models.OneToOneField(Pet, on_delete=models.CASCADE, related_name="state")
    mood = models.CharField(max_length=16, choices=MOOD_CHOICES, default="alegre")
    energy = models.PositiveSmallIntegerField(default=100)
    happiness = models.PositiveSmallIntegerField(default=100)
    days_offline = models.PositiveIntegerField(default=0)
    last_seen = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["last_seen"])]

    def __str__(self):
        return f"{self.pet.name} — {self.mood} e={self.energy} h={self.happiness}"


class PetEvent(models.Model):
    EVENT_CHOICES = [
        ("boot", "Ligou"),
        ("sleep", "Dormiu"),
        ("feed", "Alimentou"),
        ("play", "Brincou"),
        ("snake", "Jogo Snake"),
        ("reaction", "Jogo Reação"),
        ("jukebox", "Jukebox"),
    ]

    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=16, choices=EVENT_CHOICES, db_index=True)
    detail = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [models.Index(fields=["pet", "occurred_at"])]

    def __str__(self):
        return f"{self.pet.name} {self.event_type} {self.occurred_at:%Y-%m-%d %H:%M}"
