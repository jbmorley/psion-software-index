---
title: Library
layout: full
---

# Library

<ul class="applications">
    {% for application in site.data.library %}
        <li>
            <a href="/programs/{{ application.uid }}">
                <div class="application-header">
                    <div class="application-name">
                        {% if application.iconData %}
                            <img class="icon" src="{{ application.iconData }}">
                        {% endif %}
                        {{ application.name }}
                    </div>
                </div>
            </a>
        </li>
    {% endfor %}
</ul>
