---
title: Icons
layout: full
---

# Icons

<div class="icon-grid">
    {% for application in site.data.library %}
        {% if application.iconData %}
            <img class="icon" alt="{{ application.name }}" title="{{ application.name }}" src="{{ application.iconData }}">
        {% endif %}
    {% endfor %}
</div>
