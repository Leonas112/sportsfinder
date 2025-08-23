# activities/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Location, Coach, Tag, ActivityClass, ScheduleRule

class ScheduleRuleInline(admin.TabularInline):
    model = ScheduleRule
    extra = 2

@admin.register(ActivityClass)
class ActivityClassAdmin(admin.ModelAdmin):
    list_display = ("title", "location", "coach", "price", "public_link")
    list_display_links = ("title",)
    search_fields = ("title", "description")
    list_filter = ("location", "tags")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("slug",)   # optional
    inlines = [ScheduleRuleInline]

    @admin.display(description="Public")
    def public_link(self, obj):
        return format_html('<a href="{}" target="_blank">Open</a>', obj.get_absolute_url())


admin.site.register(Location)
admin.site.register(Coach)
admin.site.register(Tag)
admin.site.register(ScheduleRule)