# CSS dublikatsiyasini yo'q qilish

base.html, base_auth.html, agents/agent_base.html, clients/base_client.html
fayllarida bir xil ~600 qatorlik <style> bloki 4 marta takrorlangan.

QADAMLAR:

1. base.html dagi <style>...</style> ichidagi BARCHA CSS'ni
   static_src/css/base.css fayliga ko'chiring (loyihada
   STATICFILES_DIRS = [BASE_DIR / "static_src"] settings.py'da
   allaqachon sozlandi — yuqoridagi patchga qarang).

2. Har bir asosiy shablonning boshiga qo'shing:

   {% load static %}
   ...
   <link rel="stylesheet" href="{% static 'css/base.css' %}"/>

   va o'sha katta <style>...</style> blokini olib tashlang.

3. Sahifaga xos farqlar (masalan agent_base.html dagi "Agent panel"
   yozuvi, client_base.html dagi boshqa nav-link'lar) — bular HTML
   qismida qoladi, CSS umumiy bo'lib qoladi.

NATIJA: rangni yoki radius'ni o'zgartirish endi 1 faylda, 4 emas.
Bonus: browser bir marta yuklab, keshlaydi -> sahifalar orasida
navigatsiya tezlashadi (avval har HTML o'z ichida CSS olib yurardi).
