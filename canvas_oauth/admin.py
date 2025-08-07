from django.contrib import admin

from canvas_oauth.models import CanvasEnvironment, CanvasOAuth2Token


@admin.register(CanvasEnvironment)
class CanvasEnvironmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'domain')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(CanvasOAuth2Token)
class CanvasOAuth2TokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'environment', 'expires', 'created_on', 'updated_on')
    list_filter = ('environment', 'created_on')
    search_fields = ('user__username', 'user__email', 'environment__name')
    readonly_fields = ('created_on', 'updated_on')

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing token
            return self.readonly_fields + ('user', 'environment')
        return self.readonly_fields
