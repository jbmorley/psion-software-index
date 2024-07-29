---
title: Sources
---

# Sources

The index is built from the following sources:

<ul>
    {% for source in site.data.sources %}
        <li>
            {% if source.url %}<a href="{{ source.url }}">{% endif %}
            {% if source.name %}{{ source.name }}{% else %}{{ source.path }}{% endif %}
            {% if source.url %}</a>{% endif %}
        </li>
    {% endfor %}
</ul>
