"""
agent/models.py

Agent va AgentBalance modellari.
User → AUTH_USER_MODEL (apps.User) bilan OneToOne bog'lanadi.
"""
from django.conf import settings
from django.db.models import (
    Model, CharField, TextField, ForeignKey, OneToOneField,
    CASCADE, SET_NULL, IntegerField, DecimalField,
    DateTimeField, DateField, BooleanField,
)
from django.utils import timezone


class Agent(Model):
    # ── Login uchun User bog'lanishi ──
    user = OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=SET_NULL,
        null=True, blank=True,
        related_name='agent_profile',
        help_text="Agent panelga kirish uchun login hisobi",
    )
    first_name = CharField(max_length=120)
    last_name = CharField(max_length=120)
    phone = CharField(max_length=20)
    address = CharField(max_length=255, blank=True)
    commission_rate = DecimalField(
        max_digits=5, decimal_places=2, default=3.0,
        help_text="Foiz stavkasi, masalan 3.5",
    )
    balance_limit = IntegerField(
        default=0,
        help_text="Agentga berilishi mumkin bo'lgan maksimal naqd pul",
    )
    is_active = BooleanField(default=True)
    date_created = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name = "Agent"
        verbose_name_plural = "Agentlar"


class AgentBalance(Model):
    agent = ForeignKey(Agent, on_delete=CASCADE, related_name='balances')
    date = DateField(default=timezone.now)
    given_amount = IntegerField(default=0)
    returned_amount = IntegerField(default=0)
    note = TextField(blank=True)

    @property
    def remaining(self):
        return self.given_amount - self.returned_amount

    def __str__(self):
        return f"{self.agent} — {self.date} | Qoldi: {self.remaining}"

    class Meta:
        verbose_name = "Agent balansi"
        verbose_name_plural = "Agent balanslari"
        ordering = ['-date']
