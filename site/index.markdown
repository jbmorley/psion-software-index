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
                        {% if application.icon %}
                            <img class="icon" src="/{{ application.icon }}">
                        {% endif %}
                        {{ application.name }}
                    </div>
                </div>
            </a>
        </li>
    {% endfor %}
</ul>
