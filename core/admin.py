# core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Measurement, Goal, Message

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    
    # Opravené zobrazenie stĺpcov, používame spätné relácie `trainees`
    # a priame `helpers`
    list_display = ('username', 'email', 'role', 'get_head_trainer_name', 'get_trainees_list', 'get_helpers_list')
    list_filter = ('role',)

    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role', 'head_trainer', 'helpers')}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role', 'head_trainer', 'helpers')}),
    )
    
    # Pridávame metódy pre zobrazenie zoznamu
    def get_trainees_list(self, obj):
        return ", ".join([t.username for t in obj.trainees.all()])
    get_trainees_list.short_description = 'Trainees'

    def get_helpers_list(self, obj):
        return ", ".join([h.username for h in obj.helpers.all()])
    get_helpers_list.short_description = 'Helpers'

    def get_head_trainer_name(self, obj):
        return obj.head_trainer.username if obj.head_trainer else 'None'
    get_head_trainer_name.short_description = 'Head Trainer'

@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'weight', 'chest', 'waist')
    list_filter = ('user',)

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('user', 'description', 'target_date')
    list_filter = ('user',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'timestamp', 'is_read')
    list_filter = ('sender', 'receiver')