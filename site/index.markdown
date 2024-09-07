---
title: Library
layout: full
---

# Library

<ul class="applications">
    {% for program in site.data.programs %}
        <li>
            <a href="/programs/{{ program.uid }}">
                <div class="application-header">
                    <div class="application-name">
                        {% if program.icon %}
                            <img class="icon" src="/{{ program.icon }}">
                        {% endif %}
                        {{ program.name }}
                    </div>
                </div>
            </a>
        </li>
    {% endfor %}
</ul>
