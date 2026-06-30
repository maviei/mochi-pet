from django.contrib import admin
from .models import Pet, PetState, PetEvent


class PetStateInline(admin.StackedInline):
    model = PetState
    extra = 0


class PetEventInline(admin.TabularInline):
    model = PetEvent
    extra = 0
    readonly_fields = ["event_type", "detail", "occurred_at"]
    can_delete = False
    max_num = 0


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ["name", "skin", "current_mood", "energy", "happiness", "last_seen"]
    inlines = [PetStateInline, PetEventInline]

    @admin.display(description="Humor")
    def current_mood(self, obj):
        return obj.state.mood if hasattr(obj, "state") else "-"

    @admin.display(description="Energia")
    def energy(self, obj):
        return obj.state.energy if hasattr(obj, "state") else "-"

    @admin.display(description="Felicidade")
    def happiness(self, obj):
        return obj.state.happiness if hasattr(obj, "state") else "-"

    @admin.display(description="Última vez online")
    def last_seen(self, obj):
        return obj.state.last_seen if hasattr(obj, "state") else "-"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("state")


@admin.register(PetEvent)
class PetEventAdmin(admin.ModelAdmin):
    list_display = ["pet", "event_type", "occurred_at"]
    list_filter = ["event_type", "pet"]
    readonly_fields = ["occurred_at"]
    date_hierarchy = "occurred_at"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("pet")
