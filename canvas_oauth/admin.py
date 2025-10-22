from django.contrib import admin

from canvas_oauth.models import CanvasOAuth2Token


@admin.register(CanvasOAuth2Token)
class CanvasOAuth2TokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'expires', 'created_on', 'updated_on')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_on', 'updated_on')

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing token
            return self.readonly_fields + ('user')
        return self.readonly_fields
