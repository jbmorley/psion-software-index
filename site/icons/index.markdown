---
title: Icons
layout: full
---

# Icons

<div class="icon-grid">
    {% for application in site.data.library %}
        {% if application.iconData %}
            <a href="/programs/{{ application.uid }}">
                <img class="icon" alt="{{ application.name }}" title="{{ application.name }}" src="{{ application.iconData }}">
            </a>
        {% endif %}
    {% endfor %}
</div>
