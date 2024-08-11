---
title: Icons
layout: full
---

# Icons

<div>
    {% for application in site.data.library %}
        {% if application.iconData %}
            <img class="icon" src="{{ application.iconData }}">
        {% endif %}
    {% endfor %}
</div>
